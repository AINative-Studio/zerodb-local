"""
Lite-mode CDC -> sync-plan integration tests.

Refs #63: #47 fixed lite-mode CRUD so that api/services/{tables,vector,
events,memory,files}_service.py actually write real data to SQLite in lite
mode -- but none of those 5 services ever called cdc_service.log_change(),
so the change_log table (which sync_orchestrator.py's plan_sync() reads via
CDCService.get_unsynced_changes() to decide what needs syncing) stayed
permanently empty. The real symptom: create a project, a table, and rows via
real HTTP, then call the real POST /v1/projects/{id}/sync/plan endpoint (what
`zerodb sync plan` calls) -- it always reported zero pending changes, even
though real, never-synced local data existed.

These tests start a real uvicorn server in lite mode (ZERODB_BACKEND=lite)
and drive it over real HTTP, following the pattern in
tests/test_lite_mode_crud.py -- no mocks. Each test creates real data for one
entity type, then calls the real sync/plan endpoint and asserts it reports a
non-zero pending-changes count for that entity type.
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
    data_dir = tmp_path_factory.mktemp("zerodb_cdc_sync_data")
    os.environ["ZERODB_DATA_DIR"] = str(data_dir)

    import sys
    api_dir = os.path.join(os.path.dirname(__file__), "..", "api")
    if api_dir not in sys.path:
        sys.path.insert(0, os.path.abspath(api_dir))

    try:
        from main import app
    except Exception as exc:
        pytest.skip(f"Cannot import API app — full source tree required: {exc}")

    port = 18744  # distinct from test_lite_mode_crud.py's 18743
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
        json={"name": f"cdc-sync-test-{time.time_ns()}", "description": "lite CDC sync test"},
        timeout=10,
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]


def _sync_plan(lite_server, project_id, entity_types=None):
    """Call the real sync-plan endpoint, exactly as `zerodb sync plan` does."""
    payload = {
        "direction": "push",
        "conflict_strategy": "newest_wins",
        "include_schema": False,
    }
    if entity_types:
        payload["entity_types"] = entity_types
    resp = httpx.post(
        f"{lite_server}/v1/projects/{project_id}/sync/plan",
        json=payload,
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestSyncPlanDetectsLiteModeWrites:
    """
    Repro + fix verification for #63: every one of these previously reported
    zero pending changes because the 5 real-API service files never called
    cdc_service.log_change(), leaving change_log permanently empty in lite
    mode (unlike full mode, where PL/pgSQL triggers populate it for free).
    """

    def test_table_row_insert_is_synced(self, lite_server, project_id):
        """
        GIVEN a project with no prior activity
        WHEN a table is created and 2 rows are inserted via the real HTTP API
        THEN sync/plan reports a non-zero table_rows pending-change count

        This is the exact repro from the issue: create a project, a table,
        and 2 rows, then check sync plan.
        """
        # Baseline: nothing synced yet for a brand new project
        baseline = _sync_plan(lite_server, project_id, entity_types=["tables"])
        assert baseline["entity_counts"]["table_rows"] == 0

        create_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/tables",
            json={"table_name": "widgets", "schema": {"fields": {"name": {"type": "string"}}}},
            timeout=10,
        )
        assert create_resp.status_code == 201, create_resp.text

        insert_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/tables/widgets/insert",
            json={"rows": [{"name": "widget-a"}, {"name": "widget-b"}]},
            timeout=10,
        )
        assert insert_resp.status_code == 200, insert_resp.text
        assert insert_resp.json()["inserted_count"] == 2

        plan = _sync_plan(lite_server, project_id, entity_types=["tables"])
        assert plan["entity_counts"]["table_rows"] == 2, plan

        # The plan's own warnings must not contradict its entity_counts:
        # with real pending table_rows, "No entities to sync" must not
        # appear (it previously did, since _generate_warnings summed
        # entity_counts without table_rows -- Refs #63).
        warning_messages = [w["message"] for w in plan["warnings"]]
        assert "No entities to sync" not in warning_messages, plan

    def test_table_row_update_and_delete_are_synced_as_separate_entries(
        self, lite_server, project_id
    ):
        """
        GIVEN a table with one row
        WHEN the row is updated, then deleted
        THEN each operation shows up as its own additional pending change

        (delete_rows is a soft-delete UPDATE under the hood in both lite and
        full mode, so the row's logged change_log operation is 'UPDATE' in
        both cases -- what matters here is that the row count of unsynced
        change_log entries increases with each write, not the literal
        operation label.)
        """
        httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/tables",
            json={"table_name": "gadgets", "schema": {}},
            timeout=10,
        )
        httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/tables/gadgets/insert",
            json={"rows": [{"name": "gadget-a"}]},
            timeout=10,
        )

        after_insert = _sync_plan(lite_server, project_id, entity_types=["tables"])
        count_after_insert = after_insert["entity_counts"]["table_rows"]
        assert count_after_insert >= 1

        update_resp = httpx.put(
            f"{lite_server}/v1/projects/{project_id}/database/tables/gadgets/update",
            json={"filter": {"name": "gadget-a"}, "update": {"name": "gadget-a-renamed"}},
            timeout=10,
        )
        assert update_resp.status_code == 200, update_resp.text

        after_update = _sync_plan(lite_server, project_id, entity_types=["tables"])
        assert after_update["entity_counts"]["table_rows"] == count_after_insert + 1, after_update

        delete_resp = httpx.request(
            "DELETE",
            f"{lite_server}/v1/projects/{project_id}/database/tables/gadgets/rows",
            json={"filter": {"name": "gadget-a-renamed"}},
            timeout=10,
        )
        assert delete_resp.status_code == 200, delete_resp.text

        after_delete = _sync_plan(lite_server, project_id, entity_types=["tables"])
        assert after_delete["entity_counts"]["table_rows"] == count_after_insert + 2, after_delete

    def test_vector_upsert_is_synced(self, lite_server, project_id):
        """
        GIVEN a project with no vectors
        WHEN a vector is upserted via the real HTTP API
        THEN sync/plan reports a non-zero vectors pending-change count
        """
        baseline = _sync_plan(lite_server, project_id, entity_types=["vectors"])
        assert baseline["entity_counts"]["vectors"] == 0

        upsert_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/vectors/upsert",
            json={"document": "a lite-mode cdc test document", "metadata": {"k": "v"}},
            # Generous timeout: may be the first call to touch the local
            # embeddings service, which lazily downloads a model on first
            # use (Refs #61 -- same cold-start note as test_lite_mode_crud.py)
            timeout=90,
        )
        assert upsert_resp.status_code == 200, upsert_resp.text

        plan = _sync_plan(lite_server, project_id, entity_types=["vectors"])
        assert plan["entity_counts"]["vectors"] == 1, plan

    def test_memory_store_is_synced(self, lite_server, project_id):
        """
        GIVEN a project with no memory entries
        WHEN a memory is stored via the real HTTP API
        THEN sync/plan reports a non-zero memory pending-change count
        """
        baseline = _sync_plan(lite_server, project_id, entity_types=["memory"])
        assert baseline["entity_counts"]["memory"] == 0

        store_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/memory/store",
            json={"content": "lite-mode cdc test memory", "role": "user", "session_id": "s1"},
            timeout=30,
        )
        assert store_resp.status_code == 200, store_resp.text

        plan = _sync_plan(lite_server, project_id, entity_types=["memory"])
        assert plan["entity_counts"]["memory"] == 1, plan

    def test_event_create_is_synced(self, lite_server, project_id):
        """
        GIVEN a project with no events
        WHEN an event is created via the real HTTP API
        THEN sync/plan reports a non-zero events pending-change count
        """
        baseline = _sync_plan(lite_server, project_id, entity_types=["events"])
        assert baseline["entity_counts"]["events"] == 0

        create_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/events",
            json={"event_type": "test.event", "event_data": {"k": "v"}},
            timeout=10,
        )
        assert create_resp.status_code == 201, create_resp.text

        plan = _sync_plan(lite_server, project_id, entity_types=["events"])
        assert plan["entity_counts"]["events"] == 1, plan

    def test_file_upload_is_synced(self, lite_server, project_id):
        """
        GIVEN a project with no files
        WHEN a file is uploaded via the real HTTP API
        THEN sync/plan reports a non-zero files pending-change count
        """
        import base64

        baseline = _sync_plan(lite_server, project_id, entity_types=["files"])
        assert baseline["entity_counts"]["files"] == 0

        upload_resp = httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/files/upload",
            json={
                "file_name": "cdc-test.txt",
                "file_content": base64.b64encode(b"hello cdc").decode(),
                "content_type": "text/plain",
            },
            timeout=15,
        )
        assert upload_resp.status_code == 201, upload_resp.text

        plan = _sync_plan(lite_server, project_id, entity_types=["files"])
        assert plan["entity_counts"]["files"] == 1, plan

    def test_full_repro_table_and_rows_together(self, lite_server, project_id):
        """
        The exact end-to-end repro from the issue body: create a project
        (via the project_id fixture), a table, and 2 rows, then check both
        the sync plan's entity_counts AND the real GET .../sync/status
        endpoint's pending_changes_count report real pending changes rather
        than 'No changes to sync' (pending_changes_count == 0) -- the literal
        symptom described in the issue.
        """
        # Baseline: a brand new project has nothing pending yet
        status_resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/sync/status", timeout=10
        )
        assert status_resp.status_code == 200, status_resp.text
        assert status_resp.json()["pending_changes_count"] == 0

        httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/tables",
            json={"table_name": "repro", "schema": {}},
            timeout=10,
        )
        httpx.post(
            f"{lite_server}/v1/projects/{project_id}/database/tables/repro/insert",
            json={"rows": [{"a": 1}, {"a": 2}]},
            timeout=10,
        )

        plan = _sync_plan(lite_server, project_id)
        assert plan["entity_counts"]["table_rows"] == 2, (
            "sync plan reported zero table_rows pending changes despite "
            "real, never-synced table rows existing -- CDC logging "
            f"regression (#63). Full plan: {plan}"
        )

        status_resp = httpx.get(
            f"{lite_server}/v1/projects/{project_id}/sync/status", timeout=10
        )
        assert status_resp.status_code == 200, status_resp.text
        assert status_resp.json()["pending_changes_count"] == 2, (
            "GET .../sync/status reported zero pending changes despite "
            "real, never-synced table rows existing -- this is the exact "
            "'No changes to sync. Everything is up to date.' symptom from "
            f"the issue. Full status: {status_resp.json()}"
        )
