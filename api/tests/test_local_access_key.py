"""
Sign-in defaults and the optional local access key.

ZeroDB Local is a single-developer tool: by default it needs no login in
either backend (cloud sign-in is opt-in), and it can be locked with one
shared key (ZERODB_LOCAL_API_KEY) when the server is reachable by others.
"""
import asyncio
import importlib
import os
import sys

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_HERE, ".."))  # api/
sys.path.insert(0, os.path.join(_HERE, "..", ".."))  # repo root, for lite/


def load_auth(monkeypatch, tmp_path, **env):
    """Re-import auth with a clean, explicit environment."""
    for var in ("ZERODB_AUTH_MODE", "ZERODB_LOCAL_API_KEY", "CLOUD_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ZERODB_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ZERODB_BACKEND", env.pop("backend", "lite"))
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import lite.config  # reads ZERODB_BACKEND at import time
    import auth

    importlib.reload(lite.config)
    return importlib.reload(auth)


def bearer(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def call(auth, credentials=None):
    return asyncio.run(auth.get_current_user(credentials=credentials, db=None))


class TestDefaultAuthMode:
    def test_lite_backend_defaults_to_local(self, monkeypatch, tmp_path):
        auth = load_auth(monkeypatch, tmp_path, backend="lite")
        assert auth.AUTH_MODE == "local"

    def test_full_backend_also_defaults_to_local(self, monkeypatch, tmp_path):
        """Docker users get a working dashboard without a cloud account."""
        auth = load_auth(monkeypatch, tmp_path, backend="full")
        assert auth.AUTH_MODE == "local"

    def test_cloud_sign_in_is_opt_in(self, monkeypatch, tmp_path):
        auth = load_auth(monkeypatch, tmp_path, ZERODB_AUTH_MODE="cloud")
        assert auth.AUTH_MODE == "cloud"


class TestLocalModeWithoutKey:
    def test_returns_the_built_in_local_user(self, monkeypatch, tmp_path):
        auth = load_auth(monkeypatch, tmp_path)
        user = call(auth)
        assert user.id == "00000000-0000-0000-0000-000000000001"
        assert user.username == "local-developer"


class TestLocalAccessKey:
    def test_missing_key_is_rejected(self, monkeypatch, tmp_path):
        auth = load_auth(monkeypatch, tmp_path, ZERODB_LOCAL_API_KEY="s3cret-local-key")
        with pytest.raises(HTTPException) as exc:
            call(auth)
        assert exc.value.status_code == 401
        assert exc.value.headers == {"WWW-Authenticate": "Bearer"}

    def test_wrong_key_is_rejected(self, monkeypatch, tmp_path):
        auth = load_auth(monkeypatch, tmp_path, ZERODB_LOCAL_API_KEY="s3cret-local-key")
        with pytest.raises(HTTPException) as exc:
            call(auth, bearer("guess"))
        assert exc.value.status_code == 401

    def test_correct_key_returns_the_local_user(self, monkeypatch, tmp_path):
        auth = load_auth(monkeypatch, tmp_path, ZERODB_LOCAL_API_KEY="s3cret-local-key")
        user = call(auth, bearer("s3cret-local-key"))
        assert user.username == "local-developer"

    def test_blank_key_means_no_key(self, monkeypatch, tmp_path):
        auth = load_auth(monkeypatch, tmp_path, ZERODB_LOCAL_API_KEY="   ")
        assert call(auth).username == "local-developer"

    def test_error_never_echoes_the_key(self, monkeypatch, tmp_path):
        auth = load_auth(monkeypatch, tmp_path, ZERODB_LOCAL_API_KEY="s3cret-local-key")
        with pytest.raises(HTTPException) as exc:
            call(auth, bearer("guess"))
        assert "s3cret" not in str(exc.value.detail)
