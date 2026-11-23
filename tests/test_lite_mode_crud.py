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
from urllib.parse import quote

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

    def test_custom_vector_id_containing_slash_is_reachable(self, lite_server, project_id):
        """
        Dashboard redesign handoff (docs/features/DASHBOARD_REDESIGN.md)
        flagged: a custom vector_id like "faq/refund-policy" is a realistic
        choice for namespacing IDs by hand (VectorResponse has both `id`,
        the real DB primary key, and `vector_id`, the user's custom label --
        GET/DELETE match on either). But /vectors/{vector_id} declared the
        path param as a plain str -- FastAPI/Starlette decode the
        URL-encoded slash back into a literal "/" before routing, so a
        single path segment can never match it and the request 404s.
        """
        custom_id = "faq/refund-policy"
        upsert_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/vectors/upsert",
            json={"document": "refunds within 30 days", "vector_id": custom_id},
            timeout=90,
        )
        assert upsert_resp.status_code == 200, upsert_resp.text
        assert upsert_resp.json()["vector_id"] == custom_id

        get_resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/database/vectors/{quote(custom_id, safe='')}",
            timeout=10,
        )
        assert get_resp.status_code == 200, get_resp.text
        assert get_resp.json()["vector_id"] == custom_id

        delete_resp = httpx.delete(
            f"{lite_server}/v1/projects/{project_id}/database/vectors/{quote(custom_id, safe='')}",
            timeout=10,
        )
        assert delete_resp.status_code == 204, delete_resp.text


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
