"""
Tests for backend selector (ZERODB_BACKEND env var).

BDD-style tests covering:
- Lite mode detection
- Full mode detection
- Auto-detection from DATABASE_URL
- Service lazy loading in lite mode
- Health endpoint backend awareness

Refs #1711
"""
import importlib
import os
import sys
import types
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_config(env_overrides: dict):
    """Reload lite.config with the given env vars to test detection logic."""
    with patch.dict(os.environ, env_overrides, clear=False):
        # Remove cached module so we get a fresh _detect_backend call
        sys.modules.pop("lite.config", None)
        import lite.config as cfg
        importlib.reload(cfg)
        return cfg


# ---------------------------------------------------------------------------
# SCENARIO: Explicit ZERODB_BACKEND env var
# ---------------------------------------------------------------------------

class TestExplicitBackendSelection:
    """Given ZERODB_BACKEND is explicitly set."""

    def test_lite_mode_when_env_is_lite(self, tmp_path):
        """WHEN ZERODB_BACKEND=lite THEN is_lite_mode() returns True."""
        cfg = _reload_config({
            "ZERODB_BACKEND": "lite",
            "ZERODB_DATA_DIR": str(tmp_path / "data"),
            "ZERODB_MODELS_DIR": str(tmp_path / "models"),
        })
        assert cfg.ZERODB_BACKEND == "lite"
        assert cfg.is_lite_mode() is True
        assert cfg.is_full_mode() is False

    def test_full_mode_when_env_is_full(self, tmp_path):
        """WHEN ZERODB_BACKEND=full THEN is_full_mode() returns True."""
        cfg = _reload_config({
            "ZERODB_BACKEND": "full",
            "ZERODB_DATA_DIR": str(tmp_path / "data"),
            "ZERODB_MODELS_DIR": str(tmp_path / "models"),
        })
        assert cfg.ZERODB_BACKEND == "full"
        assert cfg.is_full_mode() is True
        assert cfg.is_lite_mode() is False

    def test_case_insensitive_backend_value(self, tmp_path):
        """WHEN ZERODB_BACKEND=LITE (uppercase) THEN it normalises to lite."""
        cfg = _reload_config({
            "ZERODB_BACKEND": "LITE",
            "ZERODB_DATA_DIR": str(tmp_path / "data"),
            "ZERODB_MODELS_DIR": str(tmp_path / "models"),
        })
        assert cfg.ZERODB_BACKEND == "lite"
        assert cfg.is_lite_mode() is True


# ---------------------------------------------------------------------------
# SCENARIO: Auto-detect from DATABASE_URL
# ---------------------------------------------------------------------------

class TestAutoDetectFromDatabaseUrl:
    """Given ZERODB_BACKEND is not set, detect from DATABASE_URL."""

    def test_full_when_postgres_url(self, tmp_path):
        """WHEN DATABASE_URL starts with postgresql:// THEN default to full."""
        cfg = _reload_config({
            "ZERODB_BACKEND": "",
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/zerodb",
            "ZERODB_DATA_DIR": str(tmp_path / "data"),
            "ZERODB_MODELS_DIR": str(tmp_path / "models"),
        })
        assert cfg.ZERODB_BACKEND == "full"

    def test_lite_when_sqlite_url(self, tmp_path):
        """WHEN DATABASE_URL does not start with postgresql:// THEN default to lite."""
        cfg = _reload_config({
            "ZERODB_BACKEND": "",
            "DATABASE_URL": "sqlite:///tmp/test.db",
            "ZERODB_DATA_DIR": str(tmp_path / "data"),
            "ZERODB_MODELS_DIR": str(tmp_path / "models"),
        })
        assert cfg.ZERODB_BACKEND == "lite"

    def test_lite_when_no_database_url(self, tmp_path):
        """WHEN DATABASE_URL is absent THEN default to lite."""
        env = {
            "ZERODB_BACKEND": "",
            "ZERODB_DATA_DIR": str(tmp_path / "data"),
            "ZERODB_MODELS_DIR": str(tmp_path / "models"),
        }
        # Ensure DATABASE_URL is truly absent
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("DATABASE_URL", None)
            sys.modules.pop("lite.config", None)
            import lite.config as cfg
            importlib.reload(cfg)
            assert cfg.ZERODB_BACKEND == "lite"


# ---------------------------------------------------------------------------
# SCENARIO: Data directory helpers
# ---------------------------------------------------------------------------

class TestDataDirectoryHelpers:
    """Given the config module is loaded, data path helpers work correctly."""

    def test_get_data_path_creates_subdirectory(self, tmp_path):
        """WHEN get_data_path("collections/default") is called THEN it creates the dir."""
        cfg = _reload_config({
            "ZERODB_BACKEND": "lite",
            "ZERODB_DATA_DIR": str(tmp_path / "data"),
            "ZERODB_MODELS_DIR": str(tmp_path / "models"),
        })
        result = cfg.get_data_path("collections/default")
        assert result.exists()
        assert result.is_dir()
        assert str(result).endswith("collections/default")

    def test_data_dir_created_on_import(self, tmp_path):
        """WHEN lite.config is imported THEN DATA_DIR exists."""
        cfg = _reload_config({
            "ZERODB_BACKEND": "lite",
            "ZERODB_DATA_DIR": str(tmp_path / "fresh_data"),
            "ZERODB_MODELS_DIR": str(tmp_path / "fresh_models"),
        })
        assert cfg.DATA_DIR.exists()
        assert cfg.MODELS_DIR.exists()


# ---------------------------------------------------------------------------
# SCENARIO: Service lazy loading in lite mode
# ---------------------------------------------------------------------------

class TestServiceLazyLoadingLiteMode:
    """Given the services package uses __getattr__ for lazy loading."""

    def test_lite_service_map_entries(self):
        """WHEN _LITE_SERVICE_MAP is defined THEN it maps the five core services."""
        # Import the init module to inspect the map
        spec = importlib.util.find_spec("services")
        if spec is None:
            pytest.skip("services package not on sys.path in test environment")

        # We can at least verify the mapping dict exists and has the right keys
        sys.modules.pop("services", None)
        import services
        importlib.reload(services)
        expected_keys = {
            "database_service",
            "qdrant_service",
            "embeddings_service",
            "minio_service",
            "redpanda_service",
        }
        assert expected_keys == set(services._LITE_SERVICE_MAP.keys())

    def test_getattr_raises_for_unknown_attribute(self):
        """WHEN accessing an unknown service THEN AttributeError is raised."""
        spec = importlib.util.find_spec("services")
        if spec is None:
            pytest.skip("services package not on sys.path in test environment")

        sys.modules.pop("services", None)
        import services
        importlib.reload(services)
        with pytest.raises(AttributeError, match="no_such_service"):
            _ = services.no_such_service

    def test_lite_mode_routes_to_lite_module(self, tmp_path, monkeypatch):
        """WHEN lite mode is active THEN __getattr__ loads from lite.services.*."""
        # Build an isolated stub "database_service_lite" module under
        # tmp_path and prepend its directory to sys.path, instead of
        # writing into the real lite/services/ package.
        # Refs #51: the previous version of this test resolved
        # Path(__file__).resolve().parent.parent / "lite" / "services" --
        # the REAL repo source tree -- and wrote into it directly (even
        # truncating the real __init__.py and unlink()-ing, rather than
        # restoring, the real ~170-line database_service_lite.py), so every
        # `pytest tests/` run permanently corrupted the working tree.
        #
        # The real "lite" and "lite.services" packages are left untouched
        # (lite.config, imported below, lives there) -- only the single
        # leaf module "lite.services.database_service_lite" is swapped for
        # a fake module object built from the isolated stub file.
        stub_dir = tmp_path / "stub_lite_services"
        stub_dir.mkdir(parents=True, exist_ok=True)
        stub_module_file = stub_dir / "database_service_lite.py"
        stub_module_file.write_text("database_service = 'lite_db_stub'\n")

        monkeypatch.syspath_prepend(str(stub_dir))

        cfg = _reload_config({
            "ZERODB_BACKEND": "lite",
            "ZERODB_DATA_DIR": str(tmp_path / "data"),
            "ZERODB_MODELS_DIR": str(tmp_path / "models"),
        })
        assert cfg.is_lite_mode() is True

        spec = importlib.util.find_spec("services")
        if spec is None:
            pytest.skip("services package not on sys.path")

        # Load the stub as a standalone module (NOT as a submodule of
        # the real "lite.services" package) and register it under the
        # dotted name that services.__getattr__ imports, so the
        # importlib.import_module("lite.services.database_service_lite")
        # call inside it resolves to our isolated stub instead of
        # touching the real file on disk. monkeypatch.setitem/delitem
        # restore sys.modules automatically on teardown.
        stub_spec = importlib.util.spec_from_file_location(
            "lite.services.database_service_lite", stub_module_file
        )
        stub_module = importlib.util.module_from_spec(stub_spec)
        stub_spec.loader.exec_module(stub_module)
        monkeypatch.setitem(
            sys.modules, "lite.services.database_service_lite", stub_module
        )
        monkeypatch.delitem(sys.modules, "services", raising=False)

        import services
        importlib.reload(services)
        result = services.database_service
        assert result == "lite_db_stub"


# ---------------------------------------------------------------------------
# SCENARIO: Health endpoint backend awareness
# ---------------------------------------------------------------------------

class TestHealthEndpointBackendAware:
    """Given the health module, it returns different checks per backend."""

    @pytest.mark.asyncio
    async def test_lite_health_includes_backend_field(self, tmp_path):
        """WHEN lite mode is active THEN health response includes backend=lite."""
        _reload_config({
            "ZERODB_BACKEND": "lite",
            "ZERODB_DATA_DIR": str(tmp_path / "data"),
            "ZERODB_MODELS_DIR": str(tmp_path / "models"),
        })

        # Reload health module to pick up new config
        sys.modules.pop("health", None)
        spec = importlib.util.find_spec("health")
        if spec is None:
            pytest.skip("health module not on sys.path in test environment")

        import health
        importlib.reload(health)

        result = await health.get_aggregated_health()
        assert result["backend"] == "lite"

    @pytest.mark.asyncio
    async def test_lite_health_checks_sqlite_faiss_filesystem(self, tmp_path):
        """WHEN lite mode is active THEN only sqlite, faiss, filesystem are checked."""
        _reload_config({
            "ZERODB_BACKEND": "lite",
            "ZERODB_DATA_DIR": str(tmp_path / "data"),
            "ZERODB_MODELS_DIR": str(tmp_path / "models"),
        })

        sys.modules.pop("health", None)
        spec = importlib.util.find_spec("health")
        if spec is None:
            pytest.skip("health module not on sys.path in test environment")

        import health
        importlib.reload(health)

        result = await health.get_aggregated_health()
        service_names = set(result["services"].keys())
        assert service_names == {"sqlite", "faiss", "filesystem"}

    @pytest.mark.asyncio
    async def test_full_health_includes_backend_field(self, tmp_path):
        """WHEN full mode is active THEN health response includes backend=full."""
        _reload_config({
            "ZERODB_BACKEND": "full",
            "ZERODB_DATA_DIR": str(tmp_path / "data"),
            "ZERODB_MODELS_DIR": str(tmp_path / "models"),
        })

        sys.modules.pop("health", None)
        spec = importlib.util.find_spec("health")
        if spec is None:
            pytest.skip("health module not on sys.path in test environment")

        import health
        importlib.reload(health)

        result = await health.get_aggregated_health()
        assert result["backend"] == "full"
        # Full mode checks these services (they may be unhealthy in test env)
        expected_services = {"postgres", "qdrant", "minio", "redpanda", "embeddings"}
        assert expected_services == set(result["services"].keys())

    @pytest.mark.asyncio
    async def test_lite_health_status_healthy(self, tmp_path):
        """WHEN all lite services are accessible THEN status is healthy."""
        data_dir = tmp_path / "data"
        _reload_config({
            "ZERODB_BACKEND": "lite",
            "ZERODB_DATA_DIR": str(data_dir),
            "ZERODB_MODELS_DIR": str(tmp_path / "models"),
        })

        sys.modules.pop("health", None)
        spec = importlib.util.find_spec("health")
        if spec is None:
            pytest.skip("health module not on sys.path in test environment")

        import health
        importlib.reload(health)

        result = await health.get_aggregated_health()
        assert result["status"] == "healthy"
        assert result["summary"]["healthy"] == 3
        assert result["summary"]["total"] == 3
