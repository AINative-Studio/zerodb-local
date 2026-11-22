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
import time
import threading

import pytest
import httpx
import uvicorn


# Force lite mode for this module, with an isolated data dir per test run
os.environ["ZERODB_BACKEND"] = "lite"
os.environ["TESTING"] = "true"


@pytest.fixture(scope="module")
def lite_server(tmp_path_factory):
    """
    GIVEN a clean SQLite-backed data directory
    WHEN the real lite-mode API server is started
    THEN it should be reachable over HTTP on a dedicated port
    """
    data_dir = tmp_path_factory.mktemp("zerodb_crud_data")
    os.environ["ZERODB_DATA_DIR"] = str(data_dir)

    import sys
    api_dir = os.path.join(os.path.dirname(__file__), "..", "api")
    if api_dir not in sys.path:
        sys.path.insert(0, os.path.abspath(api_dir))

    try:
        from main import app
    except Exception as exc:
        pytest.skip(f"Cannot import API app — full source tree required: {exc}")

    port = 18743  # distinct from test_integration_lite.py's 18742
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            resp = httpx.get(f"{base_url}/health", timeout=1)
            if resp.status_code == 200:
                break
        except httpx.ConnectError:
            time.sleep(0.2)
    else:
        pytest.fail("Lite server did not start in time")

    yield base_url

    server.should_exit = True
    thread.join(timeout=5)


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
