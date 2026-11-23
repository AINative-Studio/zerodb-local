"""
Lite-mode CRUD integration tests.

Refs #47: api/services/{tables,files,events,memory,vector}_service.py
hardcoded raw SQL for PostgreSQL's jsonb type and @> containment operator
with zero dialect branching, so every one of these services crashed
immediately against a real SQLite-backed lite-mode server. These tests
start a real uvicorn server in lite mode (ZERODB_BACKEND=lite) and drive
it over real HTTP, exercising create/insert/filter-query/update/delete for
each affected service end-to-end -- no mocks, following the pattern
established in tests/test_integration_lite.py.
"""
import os
import subprocess
import sys
import time

import pytest
import httpx

# Populated by the lite_server fixture below with the data dir it started
# the subprocess server against, so lite_server_db_path can locate the
# same on-disk SQLite file without re-deriving ZERODB_DATA_DIR itself.
_lite_server_data_dir: dict = {}


@pytest.fixture(scope="module")
def lite_server(tmp_path_factory):
    """
    GIVEN a clean SQLite-backed data directory
    WHEN the real lite-mode API server is started
    THEN it should be reachable over HTTP on a dedicated port

    Runs uvicorn in a real subprocess (not an in-process thread) rather
    than importing `main` directly into this test process. lite.config's
    ZERODB_BACKEND is a module-level constant computed once at import time
    (Refs #50/#63) -- if anything imported earlier in a shared pytest
    process (e.g. api/tests/, now in the same testpaths run) already
    triggered that evaluation with a Postgres-shaped DATABASE_URL set,
    is_lite_mode() silently returns False for the rest of that process
    regardless of the ZERODB_BACKEND env var set here, since nothing
    re-evaluates it. A subprocess gets a completely fresh interpreter and
    fresh module imports, so it's genuinely isolated from whatever else
    ran earlier in the same CI job -- independent of test file order.
    """
    data_dir = tmp_path_factory.mktemp("zerodb_crud_data")
    _lite_server_data_dir["path"] = str(data_dir)
    api_dir = os.path.join(os.path.dirname(__file__), "..", "api")
    port = 18743  # distinct from test_integration_lite.py's 18742

    env = dict(os.environ)
    env["ZERODB_BACKEND"] = "lite"
    env["TESTING"] = "true"
    env["ZERODB_DATA_DIR"] = str(data_dir)
    env.pop("DATABASE_URL", None)

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "main:app",
            "--host", "127.0.0.1", "--port", str(port),
            "--log-level", "error",
        ],
        cwd=os.path.abspath(api_dir),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    base_url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(50):
            if proc.poll() is not None:
                pytest.fail(
                    f"Lite server subprocess exited early with code {proc.returncode}"
                )
            try:
                resp = httpx.get(f"{base_url}/health", timeout=1)
                if resp.status_code == 200:
                    break
            except httpx.ConnectError:
                time.sleep(0.2)
        else:
            pytest.fail("Lite server did not start in time")

        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


@pytest.fixture(scope="module")
def lite_server_db_path(lite_server):
    """Absolute path to the lite_server's on-disk SQLite file, derived the
    same way lite/services/database_service_lite.py does (ZERODB_DATA_DIR
    plus 'zerodb.db'), for tests that need to inspect/seed it directly."""
    return os.path.join(_lite_server_data_dir["path"], "zerodb.db")


@pytest.fixture()
def project_id(lite_server):
    """A fresh project for each test, created via a real HTTP call."""
    resp = httpx.post(
        f"{lite_server}/v1/projects",
        json={"name": f"crud-test-{time.time_ns()}", "description": "lite CRUD test"},
        timeout=10,
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]


class TestHealthIsLite:
    def test_backend_is_lite(self, lite_server):
        resp = httpx.get(f"{lite_server}/health", timeout=5)
        assert resp.status_code == 200
        assert resp.json()["backend"] == "lite"


class TestTablesAndRowsCRUD:
    """
    Priority per issue #47: tables/rows is what the issue's repro focused
    on. Covers create table -> insert rows -> filter query -> update ->
    delete, all via real HTTP against the SQLite-backed server.
    """

    def test_create_table(self, lite_server, project_id):
        """
        GIVEN a project
        WHEN a table is created with a JSON schema
        THEN it returns 201 with a real id and ISO-string timestamps

        This is the exact repro from the issue: tables_service.create_table
        previously crashed with 'str' object has no attribute 'isoformat'
        because SQLite returns timestamp columns as strings, not datetimes.
        """
        resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/tables",
            json={
                "table_name": "users",
                "schema": {"fields": {"name": {"type": "string"}}},
                "description": "test table",
            },
            timeout=10,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "users"
        assert data["id"]  # must be a real id, not "None"
        assert data["id"] != "None"
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)

    def test_create_duplicate_table_rejected(self, lite_server, project_id):
        httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/tables",
            json={"table_name": "dupe", "schema": {}},
            timeout=10,
        )
        resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/tables",
            json={"table_name": "dupe", "schema": {}},
            timeout=10,
        )
        assert resp.status_code == 400

    def test_insert_query_update_delete_rows(self, lite_server, project_id):
        """
        GIVEN a table
        WHEN rows are inserted, then queried with a JSON-field filter,
             updated, and deleted
        THEN each step succeeds with real data -- covering the @> ->
             json_extract rewrite, the || -> Python-merge rewrite, and the
             NOW() -> bound-timestamp rewrite.
        """
        create_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/tables",
            json={"table_name": "people", "schema": {"fields": {"name": {"type": "string"}}}},
            timeout=10,
        )
        assert create_resp.status_code == 201, create_resp.text

        # Insert
        insert_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/tables/people/insert",
            json={"rows": [{"name": "alice", "age": 30}, {"name": "bob", "age": 25}]},
            timeout=10,
        )
        assert insert_resp.status_code == 200, insert_resp.text
        insert_data = insert_resp.json()
        assert insert_data["inserted_count"] == 2
        assert len(insert_data["inserted_ids"]) == 2
        assert all(rid != "None" for rid in insert_data["inserted_ids"])

        # Query without filter
        query_all = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/tables/people/query",
            json={"limit": 100, "offset": 0},
            timeout=10,
        )
        assert query_all.status_code == 200
        assert len(query_all.json()) == 2

        # Query with a JSON-field equality filter (replaces Postgres @>)
        query_filtered = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/tables/people/query",
            json={"filter": {"name": "alice"}, "limit": 100, "offset": 0},
            timeout=10,
        )
        assert query_filtered.status_code == 200
        filtered_rows = query_filtered.json()
        assert len(filtered_rows) == 1
        assert filtered_rows[0]["data"]["name"] == "alice"
        assert filtered_rows[0]["data"]["age"] == 30

        # Update rows matching the filter (replaces Postgres ||)
        update_resp = httpx.put(
            f"{lite_server}/v1/projects/{project_id}/database/tables/people/update",
            json={"filter": {"name": "alice"}, "update": {"age": 31}},
            timeout=10,
        )
        assert update_resp.status_code == 200, update_resp.text
        assert update_resp.json()["updated_count"] == 1

        # Verify the update merged rather than replaced the row's data
        verify_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/tables/people/query",
            json={"filter": {"name": "alice"}, "limit": 100, "offset": 0},
            timeout=10,
        )
        verified = verify_resp.json()[0]["data"]
        assert verified["age"] == 31
        assert verified["name"] == "alice"  # original field preserved by merge

        # Delete rows matching a filter (soft delete)
        delete_resp = httpx.request(
            "DELETE",
            f"{lite_server}/v1/projects/{project_id}/database/tables/people/rows",
            json={"filter": {"name": "bob"}},
            timeout=10,
        )
        assert delete_resp.status_code == 200, delete_resp.text
        assert delete_resp.json()["deleted_count"] == 1

        # Confirm the deleted row no longer appears in results
        final_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/tables/people/query",
            json={"limit": 100, "offset": 0},
            timeout=10,
        )
        remaining_names = {row["data"]["name"] for row in final_resp.json()}
        assert remaining_names == {"alice"}

    def test_get_and_list_tables(self, lite_server, project_id):
        httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/tables",
            json={"table_name": "orders", "schema": {}},
            timeout=10,
        )

        get_resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/database/tables/orders",
            timeout=10,
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "orders"

        list_resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/database/tables",
            timeout=10,
        )
        assert list_resp.status_code == 200
        assert any(t["name"] == "orders" for t in list_resp.json())

    def test_delete_table(self, lite_server, project_id):
        httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/tables",
            json={"table_name": "temp", "schema": {}},
            timeout=10,
        )
        delete_resp = httpx.delete(
            f"{lite_server}/v1/projects/{project_id}/database/tables/temp",
            timeout=10,
        )
        assert delete_resp.status_code == 204

        get_resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/database/tables/temp",
            timeout=10,
        )
        assert get_resp.status_code == 404


class TestVectorsCRUD:
    """
    Refs #47: vector_service's module-level singleton previously dispatched
    to VectorServiceLite in lite mode, whose method signature doesn't match
    any router call site at all -- every vector endpoint crashed with a
    TypeError. These tests cover the real router call shape end-to-end.
    """

    def test_upsert_search_list_get_delete(self, lite_server, project_id):
        # Generous timeout: this may be the first call in the suite to touch
        # the local embeddings service, which lazily downloads
        # BAAI/bge-small-en-v1.5 from HuggingFace Hub on first use
        # (lite/services/embeddings_service_local.py) -- a cold,
        # unauthenticated-rate-limited CI runner with no model cache can
        # legitimately take well over 30s. Refs #61.
        upsert_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/vectors/upsert",
            json={"document": "the quick brown fox", "metadata": {"a": 1}, "namespace": "default"},
            timeout=90,
        )
        assert upsert_resp.status_code == 200, upsert_resp.text
        vector = upsert_resp.json()
        vector_id = vector["id"]
        assert vector_id and vector_id != "None"
        assert vector["dimensions"] > 0

        search_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/vectors/search",
            json={"query": "quick fox", "limit": 5, "threshold": 0.1},
            timeout=30,
        )
        assert search_resp.status_code == 200, search_resp.text
        assert len(search_resp.json()) >= 1

        list_resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/database/vectors",
            params={"namespace": "default"},
            timeout=10,
        )
        assert list_resp.status_code == 200
        assert any(v["id"] == vector_id for v in list_resp.json())

        get_resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/database/vectors/{vector_id}",
            timeout=10,
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == vector_id

        delete_resp = httpx.delete(
            f"{lite_server}/v1/projects/{project_id}/database/vectors/{vector_id}",
            timeout=10,
        )
        assert delete_resp.status_code == 204

        get_after_delete = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/database/vectors/{vector_id}",
            timeout=10,
        )
        assert get_after_delete.status_code == 404

    def test_search_does_not_crash_when_shared_index_contains_a_memory_payload(self, lite_server, project_id):
        """
        Dashboard redesign e2e verification (docs/features/DASHBOARD_REDESIGN.md)
        caught this live, reproducibly, with a BRAND NEW vector immediately
        after upsert: Vectors and Memory share one underlying FAISS
        index/metadata store in lite mode (api/services/qdrant_service.py's
        module-level `qdrant_service` singleton resolves to one shared
        FAISSService for both features). Vectors write payload["document"];
        Memory writes payload["content"] with no "document" key at all. The
        vectors search endpoint's VectorSearchResult schema requires
        `document: str` (non-optional) and does `payload.get("document")`
        on every FAISS-ranked candidate -- so once the shared index contains
        even one memory-shaped entry, any vector search whose over-fetch
        ranks that entry into the candidate set 500s the ENTIRE response,
        rather than just skipping that one non-vector hit. Refs #87.
        """
        # Store a memory first -- this writes a payload shape with no
        # "document" key into the SAME shared FAISS index vectors search
        # reads from.
        memory_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/memory/store",
            json={"content": "the quick brown fox memory", "role": "user", "agent_id": "default"},
            timeout=90,
        )
        assert memory_resp.status_code == 200, memory_resp.text

        upsert_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/vectors/upsert",
            json={"document": "the quick brown fox vector", "namespace": "default", "metadata": {}},
            timeout=90,
        )
        assert upsert_resp.status_code == 200, upsert_resp.text

        search_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/vectors/search",
            json={"query": "quick brown fox", "limit": 10, "threshold": 0.0},
            timeout=30,
        )
        assert search_resp.status_code == 200, (
            f"Vector search must not 500 when the shared FAISS index also "
            f"contains memory-shaped payloads: {search_resp.text}"
        )

    def test_list_vectors_with_no_namespace_filter_returns_all_namespaces(self, lite_server, project_id):
        """
        Dashboard redesign e2e verification (docs/features/DASHBOARD_REDESIGN.md)
        caught this live: the dashboard's Vectors page has an "All namespaces"
        filter that, when empty, is meant to omit the namespace param entirely
        -- GET /vectors with no namespace query param should return vectors
        from every namespace in the project, not just "default". Confirmed
        live: a vector upserted into namespace "faq" was correctly stored and
        directly retrievable (?namespace=faq, or by ID), but GET /vectors with
        no namespace param at all came back empty -- because the router
        declares `namespace: str = "default"`, so an omitted param silently
        becomes the literal string "default" rather than "no filter", and the
        underlying SQL always has `AND namespace = :namespace` with no
        no-filter branch. The project's own usage counter correctly showed
        vectors=1, proving the data was there and only the list query was
        broken.
        """
        upsert_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/vectors/upsert",
            json={"document": "refunds within 30 days", "namespace": "faq", "metadata": {}},
            timeout=90,
        )
        assert upsert_resp.status_code == 200, upsert_resp.text
        vector_id = upsert_resp.json()["id"]

        # Sanity: explicitly filtering by the real namespace finds it.
        filtered = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/database/vectors",
            params={"namespace": "faq"},
            timeout=10,
        )
        assert filtered.status_code == 200
        assert any(v["id"] == vector_id for v in filtered.json())

        # The actual bug: omitting namespace entirely (the dashboard's "All
        # namespaces" state) must also find it, not silently filter to
        # "default" and hide every other namespace's vectors.
        unfiltered = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/database/vectors",
            timeout=10,
        )
        assert unfiltered.status_code == 200
        assert any(v["id"] == vector_id for v in unfiltered.json()), (
            "GET /vectors with no namespace param must return vectors from "
            "every namespace, not silently default to namespace='default'"
        )


class TestVectorDataDirIsolation:
    """
    Refs #88: `api/services/qdrant_service.py`'s module-level `qdrant_service`
    singleton calls `FAISSService()` with no arguments in lite mode, which
    defaults to `~/.zerodb/data` (`lite/services/faiss_service.py`'s
    `__init__`). It never reads `lite.config.DATA_DIR` -- the same
    ZERODB_DATA_DIR-derived constant `DatabaseServiceLite` (SQLite) and
    everything else in the app correctly uses. So two independent
    `zerodb serve --data-dir <X>` processes, each meant to be fully
    isolated per the "local-first, this project's own data" design, instead
    silently share ONE global FAISS vector store at `~/.zerodb/data`,
    regardless of what `--data-dir` either was started with -- confirmed
    live: a vector upserted against one `--data-dir` never produces a
    `vectors.faiss`/`vectors_meta.json` file in that directory at all.

    This test starts two real, separate lite-mode server subprocesses with
    two distinct, disposable data directories (not the shared module-scoped
    `lite_server` fixture, which only runs one server) and confirms a vector
    upserted against server A is only ever searchable from server A, never
    from server B.
    """

    @staticmethod
    def _start_server(data_dir: str, port: int):
        api_dir = os.path.join(os.path.dirname(__file__), "..", "api")
        env = dict(os.environ)
        env["ZERODB_BACKEND"] = "lite"
        env["TESTING"] = "true"
        env["ZERODB_DATA_DIR"] = data_dir
        env.pop("DATABASE_URL", None)

        proc = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "main:app",
                "--host", "127.0.0.1", "--port", str(port),
                "--log-level", "error",
            ],
            cwd=os.path.abspath(api_dir),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        base_url = f"http://127.0.0.1:{port}"
        for _ in range(50):
            if proc.poll() is not None:
                pytest.fail(f"Lite server subprocess exited early with code {proc.returncode}")
            try:
                if httpx.get(f"{base_url}/health", timeout=1).status_code == 200:
                    return proc, base_url
            except httpx.ConnectError:
                time.sleep(0.2)
        pytest.fail("Lite server did not start in time")

    def test_vector_data_isolated_between_two_data_dirs(self, tmp_path_factory):
        data_dir_a = str(tmp_path_factory.mktemp("zerodb_isolation_a"))
        data_dir_b = str(tmp_path_factory.mktemp("zerodb_isolation_b"))

        proc_a, url_a = self._start_server(data_dir_a, 18744)
        try:
            proc_b, url_b = self._start_server(data_dir_b, 18745)
            try:
                project_a = httpx.post(
                    f"{url_a}/v1/projects",
                    json={"name": "isolation-test-a", "description": ""},
                    timeout=10,
                ).json()["id"]
                project_b = httpx.post(
                    f"{url_b}/v1/projects",
                    json={"name": "isolation-test-b", "description": ""},
                    timeout=10,
                ).json()["id"]

                upsert_resp = httpx.post(
                    f"{url_a}/v1/projects/{project_a}/database/vectors/upsert",
                    json={"document": "isolation marker unique phrase xyzzy", "namespace": "default", "metadata": {}},
                    timeout=90,
                )
                assert upsert_resp.status_code == 200, upsert_resp.text

                # The FAISS index/metadata files must land under THIS
                # server's own --data-dir, not the global ~/.zerodb/data
                # default.
                assert os.path.exists(os.path.join(data_dir_a, "vectors.faiss")), (
                    "Server A's FAISS index was not written to its own --data-dir -- "
                    "the shared qdrant_service singleton is still using the hardcoded "
                    "~/.zerodb/data default instead of this server's configured data dir."
                )

                # Server B (different --data-dir, different process) must
                # NOT see server A's vector via search.
                search_b = httpx.post(
                    f"{url_b}/v1/projects/{project_b}/database/vectors/search",
                    json={"query": "isolation marker unique phrase xyzzy", "limit": 10, "threshold": 0.0},
                    timeout=30,
                )
                assert search_b.status_code == 200, search_b.text
                assert search_b.json() == [], (
                    "Server B found a vector that was only ever upserted against "
                    "server A's --data-dir -- the two servers are sharing one global "
                    "FAISS index instead of being isolated per --data-dir."
                )
            finally:
                proc_b.terminate()
                try:
                    proc_b.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc_b.kill()
                    proc_b.wait(timeout=5)
        finally:
            proc_a.terminate()
            try:
                proc_a.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc_a.kill()
                proc_a.wait(timeout=5)


class TestEventsCRUD:
    """Refs #47: events_service hardcoded CAST(... AS jsonb) and crashed on
    .isoformat() against SQLite's string timestamps."""

    def test_create_list_get_stats(self, lite_server, project_id):
        create_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/events",
            json={
                "event_type": "user.signup",
                "event_data": {"user_id": "abc"},
                "source": "test",
                "correlation_id": "trace-1",
            },
            timeout=10,
        )
        assert create_resp.status_code == 201, create_resp.text
        event = create_resp.json()
        assert event["id"] and event["id"] != "None"
        assert event["event_data"] == {"user_id": "abc"}
        assert isinstance(event["timestamp"], str)

        list_resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/database/events",
            timeout=10,
        )
        assert list_resp.status_code == 200
        assert any(e["id"] == event["id"] for e in list_resp.json())

        get_resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/database/events/{event['id']}",
            timeout=10,
        )
        assert get_resp.status_code == 200

        stats_resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/database/events/stats/summary",
            params={"time_range": "day"},
            timeout=10,
        )
        assert stats_resp.status_code == 200, stats_resp.text
        assert stats_resp.json()["total_events"] >= 1


class TestMemoryCRUD:
    """Refs #47: memory_service hardcoded CAST(... AS vector) and
    CAST(... AS jsonb), plus crashed on .isoformat()."""

    def test_store_search_context_sessions_delete(self, lite_server, project_id):
        store_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/memory/store",
            json={
                "content": "hello, my name is alice",
                "role": "user",
                "agent_id": "agent1",
                "session_id": "sess1",
            },
            timeout=30,
        )
        assert store_resp.status_code == 200, store_resp.text
        memory = store_resp.json()
        assert memory["id"] and memory["id"] != "None"

        search_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/memory/search",
            json={"query": "alice", "limit": 5, "threshold": 0.1},
            timeout=30,
        )
        assert search_resp.status_code == 200, search_resp.text
        assert len(search_resp.json()) >= 1

        context_resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/database/memory/context/sess1",
            params={"limit": 50},
            timeout=10,
        )
        assert context_resp.status_code == 200
        assert context_resp.json()["message_count"] == 1

        sessions_resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/database/memory/sessions",
            timeout=10,
        )
        assert sessions_resp.status_code == 200
        assert any(s["session_id"] == "sess1" for s in sessions_resp.json())

        delete_resp = httpx.delete(
            f"{lite_server}/v1/projects/{project_id}/database/memory/sessions/sess1",
            timeout=10,
        )
        assert delete_resp.status_code == 204

        context_after_delete = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/database/memory/context/sess1",
            params={"limit": 50},
            timeout=10,
        )
        assert context_after_delete.json()["message_count"] == 0


class TestFilesCRUD:
    """Refs #47: files_service hardcoded CAST(... AS jsonb)/NOW(), plus
    download_file assumed a MinIO-style response object that the lite
    FilesystemService backend doesn't return."""

    def test_upload_list_metadata_download_delete(self, lite_server, project_id):
        import base64

        content = b"hello file content"
        upload_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/files/upload",
            json={
                "file_name": "test.txt",
                "file_content": base64.b64encode(content).decode(),
                "content_type": "text/plain",
                "metadata": {"k": "v"},
            },
            timeout=15,
        )
        assert upload_resp.status_code == 201, upload_resp.text
        file_obj = upload_resp.json()
        file_id = file_obj["id"]
        assert file_id and file_id != "None"
        assert file_obj["metadata"] == {"k": "v"}

        list_resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/database/files",
            timeout=10,
        )
        assert list_resp.status_code == 200
        assert any(f["id"] == file_id for f in list_resp.json())

        meta_resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/database/files/{file_id}/metadata",
            timeout=10,
        )
        assert meta_resp.status_code == 200

        download_resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/database/files/{file_id}",
            timeout=10,
        )
        assert download_resp.status_code == 200, download_resp.text
        decoded = base64.b64decode(download_resp.json()["content"])
        assert decoded == content

        delete_resp = httpx.delete(
            f"{lite_server}/v1/projects/{project_id}/database/files/{file_id}",
            timeout=10,
        )
        assert delete_resp.status_code == 204


class TestSyncPlanWithSchemaComparison:
    """Refs #68: schema_diff_service.py's _get_postgres_tables did
    `table_schema.get('fields', {})` on the tables.schema column's raw
    value, which psycopg2 auto-deserializes to a dict in full mode but
    SQLite returns as a plain JSON string -- crashed sync/plan's default
    include_schema=True path in lite mode as soon as any table existed."""

    def test_sync_plan_with_schema_comparison_after_table_exists(
        self, lite_server, project_id
    ):
        create_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/tables",
            json={"table_name": "widgets", "schema": {"name": "string"}},
            timeout=10,
        )
        assert create_resp.status_code == 201, create_resp.text

        plan_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/sync/plan",
            json={
                "direction": "push",
                "conflict_strategy": "newest_wins",
                "include_schema": True,
            },
            timeout=15,
        )
        assert plan_resp.status_code == 200, plan_resp.text


class TestSyncStatusAndHistory:
    """Refs #73: the Sync page's two read endpoints against a fresh lite
    database. api/models/sync_history.py's SyncHistory ORM model declares
    sync_id/direction/mode/bytes_transferred/error_message/error_stack/
    snapshot_id/updated_at (matching the full/Postgres schema), but
    lite/db/schema_lite.sql's sync_history table only had the older,
    simpler shape (sync_direction/sync_mode/errors, no sync_id) -- any ORM
    query against sync_history in lite mode hit a column mismatch.
    sync_state's lite schema already matched the ORM model 1:1, so only
    sync_history needed a schema fix."""

    def test_sync_status_on_fresh_project(self, lite_server, project_id):
        """GET /sync/status must not 503 on a brand new project with no
        sync activity yet."""
        resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/sync/status",
            timeout=10,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["project_id"] == project_id
        assert body["entity_sync_states"] == {}

    def test_sync_history_on_fresh_project(self, lite_server, project_id):
        """GET /sync/history must not 503 on a brand new project with no
        sync history yet -- this is the endpoint that hit
        'no such column: sync_history.sync_id'."""
        resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/sync/history",
            timeout=10,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["items"] == []

    def test_sync_history_round_trips_a_real_entry(
        self, lite_server, lite_server_db_path, project_id
    ):
        """Write a real row directly into the running server's on-disk
        SQLite file (raw sqlite3, no ORM/mocks -- deliberately avoiding an
        in-process `database.py`/`lite.config` import, since those modules
        compute ZERODB_BACKEND/ZERODB_DATA_DIR at import time and would
        silently diverge from the subprocess server's env per the
        `lite_server` fixture's docstring), then read it back over the
        real HTTP endpoint -- confirms sync_id (and the other columns the
        full-mode ORM model expects: direction, mode, bytes_transferred,
        error_message, snapshot_id, updated_at) actually round-trip, not
        just that an empty-list query succeeds.

        Not driven through POST /sync/execute: execute's only path to a
        sync_plan currently needs the sync_plans table, which
        lite/db/schema_lite.sql does not define at all -- a separate,
        larger gap than this issue (#73) covers. See the
        DASHBOARD_REDESIGN.md follow-ups note for that gap.

        UUID columns use SQLAlchemy's `postgresql.UUID(as_uuid=True)` type
        (shared with the full-mode model), which on the SQLite dialect
        binds/compares values as 32-char dash-less hex -- not the dashed
        str(uuid.UUID) form. The raw insert below stores ids the same way
        the ORM actually would, so the read-back through the real
        project_id-filtered endpoint exercises the real storage format.
        """
        import sqlite3
        import uuid as uuid_mod

        sync_id = uuid_mod.uuid4()
        conn = sqlite3.connect(lite_server_db_path)
        try:
            conn.execute(
                """
                INSERT INTO sync_history
                    (id, project_id, sync_id, direction, mode, status,
                     records_synced, bytes_transferred)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid_mod.uuid4().hex, uuid_mod.UUID(project_id).hex,
                    sync_id.hex, "push", "full", "completed", "{}", 0,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        history_resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/sync/history",
            timeout=10,
        )
        assert history_resp.status_code == 200, history_resp.text
        items = history_resp.json()["items"]
        assert len(items) == 1
        assert items[0]["sync_id"] == str(sync_id)
        assert items[0]["direction"] == "push"
        assert items[0]["mode"] == "full"


class TestSyncConflicts:
    """Refs #79: GET /sync/conflicts/ on a fresh lite database. Same shape
    as #73's sync_history fix -- api/models/conflict_log.py's ConflictLog
    ORM model expects local_version/cloud_version/chosen_version/
    detected_at/conflict_metadata/notes (matching the full/Postgres
    migration it mirrors), but lite/db/schema_lite.sql's conflict_log table
    had an older, different shape (local_value/cloud_value/
    local_timestamp/cloud_timestamp/resolved_value, no detected_at/
    conflict_metadata/notes at all) -- any ORM query against conflict_log
    in lite mode hit the column mismatch."""

    def test_list_conflicts_on_fresh_project(self, lite_server, project_id):
        resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/sync/conflicts/",
            params={"limit": 100},
            timeout=10,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json() == []

    def test_conflicts_round_trips_a_real_entry(
        self, lite_server, lite_server_db_path, project_id
    ):
        """Seed a real conflict_log row directly on-disk (raw sqlite3, same
        reasoning as TestSyncStatusAndHistory's round-trip test for why not
        an in-process database.py import), then read it back over the real
        HTTP endpoint -- confirms the ORM-expected columns actually
        round-trip."""
        import json
        import sqlite3
        import uuid as uuid_mod

        conflict_id = uuid_mod.uuid4()
        conn = sqlite3.connect(lite_server_db_path)
        try:
            conn.execute(
                """
                INSERT INTO conflict_log
                    (id, project_id, entity_type, entity_id, local_version,
                     cloud_version, resolution_strategy, chosen_version,
                     detected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                """,
                (
                    conflict_id.hex, uuid_mod.UUID(project_id).hex,
                    "vector", "vec-1",
                    json.dumps({"text": "local"}), json.dumps({"text": "cloud"}),
                    "newest_wins", json.dumps({"text": "cloud"}),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/sync/conflicts/",
            params={"limit": 100},
            timeout=10,
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert len(items) == 1
        assert items[0]["entity_type"] == "vector"
        assert items[0]["resolution_strategy"] == "newest_wins"
