"""
Every API router sits behind the sign-in check, not just the ones that
declared it per route. Before this, the sync, export, logs and history
routers answered anyone -- in cloud mode and with a local access key alike.
/health stays open so the dashboard can show server status before sign-in.
"""
import os
import sys
import uuid

import pytest

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_HERE, "..", ".."))

KEY = "test-local-key-123"
PID = str(uuid.uuid4())

# One endpoint from each router that used to have no auth dependency.
PREVIOUSLY_OPEN = [
    ("get", "/v1/logs"),
    ("get", f"/v1/projects/{PID}/sync/status"),
    ("get", f"/v1/projects/{PID}/sync/history"),
    ("get", f"/v1/projects/{PID}/sync/export/preview"),
    ("get", f"/v1/projects/{PID}/sync/pull/preview"),
    ("get", f"/v1/projects/{PID}/cloud/status"),
]


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("ZERODB_BACKEND", "lite")
    monkeypatch.setenv("ZERODB_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ZERODB_LOCAL_API_KEY", KEY)
    monkeypatch.delenv("ZERODB_AUTH_MODE", raising=False)
    monkeypatch.delenv("CLOUD_API_KEY", raising=False)
    # Fresh imports so module-level config picks up this environment.
    for name in list(sys.modules):
        if name in ("main", "auth", "database", "lite.config") or name.startswith(("routers", "services")):
            del sys.modules[name]
    from fastapi.testclient import TestClient
    import main

    return TestClient(main.app, raise_server_exceptions=False)


def test_health_stays_open(client):
    assert client.get("/health").status_code == 200


@pytest.mark.parametrize("method,path", PREVIOUSLY_OPEN)
def test_previously_open_routes_now_require_the_key(client, method, path):
    res = getattr(client, method)(path)
    assert res.status_code == 401
    assert "ZERODB_LOCAL_API_KEY" in res.text


@pytest.mark.parametrize("method,path", PREVIOUSLY_OPEN)
def test_the_key_gets_past_sign_in(client, method, path):
    res = getattr(client, method)(path, headers={"Authorization": f"Bearer {KEY}"})
    # The route may still fail for its own reasons (no cloud link, empty
    # lite DB); what matters is that sign-in no longer turns it away.
    assert "ZERODB_LOCAL_API_KEY" not in res.text
