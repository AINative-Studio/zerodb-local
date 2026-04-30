"""
Test suite for zerodb serve command

Refs #1712: zerodb serve CLI command - one-command local server
TDD: Tests written alongside implementation with BDD-style structure
"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from typer.testing import CliRunner


@pytest.fixture
def runner():
    """CLI test runner"""
    return CliRunner()


@pytest.fixture
def serve_app():
    """Import serve app for testing"""
    from commands.serve import app
    return app


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Provide a temporary data directory"""
    return tmp_path / "zerodb_test_data"


# ===== Help Output Tests =====

class TestServeHelp:
    """Scenario: User runs zerodb serve --help"""

    def test_help_shows_command_description(self, runner, serve_app):
        """Given the serve command, help should describe its purpose"""
        result = runner.invoke(serve_app, ["--help"])

        assert result.exit_code == 0
        assert "Start ZeroDB local server" in result.stdout or "server" in result.stdout.lower()

    def test_help_shows_port_option(self, runner, serve_app):
        """Given the serve command, help should show --port option"""
        result = runner.invoke(serve_app, ["--help"])

        assert result.exit_code == 0
        assert "--port" in result.stdout

    def test_help_shows_data_dir_option(self, runner, serve_app):
        """Given the serve command, help should show --data-dir option"""
        result = runner.invoke(serve_app, ["--help"])

        assert result.exit_code == 0
        assert "--data-dir" in result.stdout

    def test_help_shows_cloud_key_option(self, runner, serve_app):
        """Given the serve command, help should show --cloud-key option"""
        result = runner.invoke(serve_app, ["--help"])

        assert result.exit_code == 0
        assert "--cloud-key" in result.stdout

    def test_help_shows_host_option(self, runner, serve_app):
        """Given the serve command, help should show --host option"""
        result = runner.invoke(serve_app, ["--help"])

        assert result.exit_code == 0
        assert "--host" in result.stdout

    def test_help_shows_reload_option(self, runner, serve_app):
        """Given the serve command, help should show --reload option"""
        result = runner.invoke(serve_app, ["--help"])

        assert result.exit_code == 0
        assert "--reload" in result.stdout


# ===== Default Configuration Tests =====

class TestServeDefaults:
    """Scenario: User runs zerodb serve with no arguments"""

    def test_default_port_is_8000(self):
        """Given no --port flag, the default port should be 8000"""
        from commands.serve import DEFAULT_PORT

        assert DEFAULT_PORT == 8000

    def test_default_host_is_all_interfaces(self):
        """Given no --host flag, the default host should bind to all interfaces"""
        from commands.serve import DEFAULT_HOST

        assert DEFAULT_HOST == "0.0.0.0"

    def test_default_data_dir_is_home_zerodb(self):
        """Given no --data-dir flag, the default should be ~/.zerodb/data/"""
        from commands.serve import DEFAULT_DATA_DIR

        expected = Path.home() / ".zerodb" / "data"
        assert DEFAULT_DATA_DIR == expected

    @patch("commands.serve.uvicorn")
    def test_serve_calls_uvicorn_with_defaults(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given default args, uvicorn.run should be called with port 8000"""
        result = runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir)])

        mock_uvicorn.run.assert_called_once_with(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info",
        )


# ===== Custom Port Tests =====

class TestServeCustomPort:
    """Scenario: User runs zerodb serve --port 9000"""

    @patch("commands.serve.uvicorn")
    def test_custom_port_is_passed_to_uvicorn(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given --port 9000, uvicorn.run should receive port=9000"""
        result = runner.invoke(serve_app, ["--port", "9000", "--data-dir", str(tmp_data_dir)])

        mock_uvicorn.run.assert_called_once()
        _, kwargs = mock_uvicorn.run.call_args
        assert kwargs["port"] == 9000

    @patch("commands.serve.uvicorn")
    def test_custom_port_with_short_flag(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given -p 3000, uvicorn.run should receive port=3000"""
        result = runner.invoke(serve_app, ["-p", "3000", "--data-dir", str(tmp_data_dir)])

        mock_uvicorn.run.assert_called_once()
        _, kwargs = mock_uvicorn.run.call_args
        assert kwargs["port"] == 3000


# ===== Data Directory Tests =====

class TestServeDataDir:
    """Scenario: Data directory is created on first run"""

    @patch("commands.serve.uvicorn")
    def test_data_dir_is_created_if_missing(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given a non-existent data dir, serve should create it"""
        assert not tmp_data_dir.exists()

        result = runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir)])

        assert tmp_data_dir.exists()
        assert tmp_data_dir.is_dir()

    @patch("commands.serve.uvicorn")
    def test_data_dir_not_recreated_if_exists(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given an existing data dir, serve should not fail"""
        tmp_data_dir.mkdir(parents=True)
        marker = tmp_data_dir / "existing_file.txt"
        marker.write_text("keep me")

        result = runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir)])

        assert result.exit_code == 0
        assert marker.read_text() == "keep me"

    @patch("commands.serve.uvicorn")
    def test_custom_data_dir_with_short_flag(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given -d /custom/path, it should use that directory"""
        result = runner.invoke(serve_app, ["-d", str(tmp_data_dir)])

        assert tmp_data_dir.exists()

    @patch("commands.serve.uvicorn")
    def test_nested_data_dir_created(self, mock_uvicorn, runner, serve_app, tmp_path):
        """Given a deeply nested path, all parent dirs should be created"""
        deep_dir = tmp_path / "a" / "b" / "c" / "data"

        result = runner.invoke(serve_app, ["--data-dir", str(deep_dir)])

        assert deep_dir.exists()


# ===== Environment Variable Tests =====

class TestServeEnvironment:
    """Scenario: Environment variables are configured before server start"""

    @patch("commands.serve.uvicorn")
    def test_backend_env_set_to_lite(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given serve runs, ZERODB_BACKEND should be 'lite'"""
        result = runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir)])

        assert os.environ.get("ZERODB_BACKEND") == "lite"

    @patch("commands.serve.uvicorn")
    def test_data_dir_env_is_set(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given serve runs, ZERODB_DATA_DIR should match --data-dir"""
        result = runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir)])

        assert os.environ.get("ZERODB_DATA_DIR") == str(tmp_data_dir)

    @patch("commands.serve.uvicorn")
    def test_cloud_key_env_set_when_provided(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given --cloud-key sk-test, ZERODB_CLOUD_KEY should be set"""
        result = runner.invoke(serve_app, [
            "--data-dir", str(tmp_data_dir),
            "--cloud-key", "sk-test-key-123",
        ])

        assert os.environ.get("ZERODB_CLOUD_KEY") == "sk-test-key-123"

    @patch("commands.serve.uvicorn")
    def test_cloud_key_env_not_set_when_absent(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given no --cloud-key, ZERODB_CLOUD_KEY should not be set"""
        # Clean up from previous tests
        os.environ.pop("ZERODB_CLOUD_KEY", None)

        result = runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir)])

        assert os.environ.get("ZERODB_CLOUD_KEY") is None


# ===== Embedding Model Tests =====

class TestServeEmbeddingModel:
    """Scenario: Embedding model is downloaded on first run"""

    @patch("commands.serve.uvicorn")
    def test_marker_file_created_on_first_run(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given first run, a model marker file should be created"""
        from commands.serve import EMBEDDING_MODEL_MARKER

        result = runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir)])

        marker = tmp_data_dir / EMBEDDING_MODEL_MARKER
        assert marker.exists()

    @patch("commands.serve.uvicorn")
    def test_model_not_redownloaded_on_subsequent_runs(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given marker exists, model download should be skipped"""
        from commands.serve import EMBEDDING_MODEL_MARKER

        tmp_data_dir.mkdir(parents=True)
        marker = tmp_data_dir / EMBEDDING_MODEL_MARKER
        marker.touch()

        # Track console output — no download message expected
        result = runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir)])

        assert result.exit_code == 0
        assert "Downloading" not in result.stdout


# ===== Startup Banner Tests =====

class TestServeStartupBanner:
    """Scenario: User sees a banner when the server starts"""

    @patch("commands.serve.uvicorn")
    def test_banner_shows_url(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given serve starts, the banner should display the URL"""
        result = runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir)])

        assert "http://localhost:8000" in result.stdout

    @patch("commands.serve.uvicorn")
    def test_banner_shows_custom_port_url(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given --port 9000, the banner should display port 9000"""
        result = runner.invoke(serve_app, [
            "--port", "9000",
            "--data-dir", str(tmp_data_dir),
        ])

        assert "http://localhost:9000" in result.stdout

    @patch("commands.serve.uvicorn")
    def test_banner_shows_backend_type(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given serve starts, the banner should show backend type as lite"""
        result = runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir)])

        assert "lite" in result.stdout

    @patch("commands.serve.uvicorn")
    def test_banner_shows_data_dir(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given serve starts, the banner should show the data directory"""
        result = runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir)])

        # Rich may line-wrap long paths inside panels, so collapse
        # whitespace before checking for the path string
        collapsed = result.stdout.replace("\n", "").replace(" ", "")
        expected = str(tmp_data_dir).replace(" ", "")
        assert expected in collapsed

    @patch("commands.serve.uvicorn")
    def test_banner_shows_zerodb_branding(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given serve starts, the banner should mention ZeroDB"""
        result = runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir)])

        assert "ZeroDB" in result.stdout


# ===== Uvicorn Integration Tests =====

class TestServeUvicornIntegration:
    """Scenario: Server is started with correct uvicorn configuration"""

    @patch("commands.serve.uvicorn")
    def test_uvicorn_receives_app_string(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given serve runs, uvicorn should load app.main:app"""
        result = runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir)])

        args, kwargs = mock_uvicorn.run.call_args
        assert args[0] == "app.main:app"

    @patch("commands.serve.uvicorn")
    def test_uvicorn_receives_custom_host(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given --host 127.0.0.1, uvicorn should bind to that host"""
        result = runner.invoke(serve_app, [
            "--host", "127.0.0.1",
            "--data-dir", str(tmp_data_dir),
        ])

        _, kwargs = mock_uvicorn.run.call_args
        assert kwargs["host"] == "127.0.0.1"

    @patch("commands.serve.uvicorn")
    def test_uvicorn_reload_default_off(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given no --reload flag, reload should be False"""
        result = runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir)])

        _, kwargs = mock_uvicorn.run.call_args
        assert kwargs["reload"] is False

    @patch("commands.serve.uvicorn")
    def test_uvicorn_reload_enabled(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given --reload, uvicorn should have reload=True"""
        result = runner.invoke(serve_app, [
            "--reload",
            "--data-dir", str(tmp_data_dir),
        ])

        _, kwargs = mock_uvicorn.run.call_args
        assert kwargs["reload"] is True

    @patch("commands.serve.uvicorn")
    def test_uvicorn_log_level_info(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given serve runs, uvicorn log level should be info"""
        result = runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir)])

        _, kwargs = mock_uvicorn.run.call_args
        assert kwargs["log_level"] == "info"


# ===== Unit Function Tests =====

class TestServeFunctions:
    """Scenario: Individual serve functions work correctly in isolation"""

    def test_ensure_data_dir_creates_directory(self, tmp_path):
        """Given a non-existent path, ensure_data_dir should create it"""
        from commands.serve import ensure_data_dir

        new_dir = tmp_path / "new_data"
        ensure_data_dir(new_dir)

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_data_dir_handles_existing(self, tmp_path):
        """Given an existing path, ensure_data_dir should not raise"""
        from commands.serve import ensure_data_dir

        existing = tmp_path / "existing"
        existing.mkdir()

        ensure_data_dir(existing)  # Should not raise
        assert existing.exists()

    def test_setup_environment_sets_backend(self, tmp_path):
        """Given a call to setup_environment, ZERODB_BACKEND should be lite"""
        from commands.serve import setup_environment

        setup_environment(tmp_path)

        assert os.environ["ZERODB_BACKEND"] == "lite"

    def test_setup_environment_sets_data_dir(self, tmp_path):
        """Given a call to setup_environment, ZERODB_DATA_DIR should be set"""
        from commands.serve import setup_environment

        setup_environment(tmp_path)

        assert os.environ["ZERODB_DATA_DIR"] == str(tmp_path)

    def test_setup_environment_sets_cloud_key(self, tmp_path):
        """Given a cloud_key, ZERODB_CLOUD_KEY should be set"""
        from commands.serve import setup_environment

        setup_environment(tmp_path, cloud_key="sk-abc")

        assert os.environ["ZERODB_CLOUD_KEY"] == "sk-abc"

    def test_setup_environment_skips_cloud_key_when_none(self, tmp_path):
        """Given no cloud_key, ZERODB_CLOUD_KEY should not be set"""
        from commands.serve import setup_environment

        os.environ.pop("ZERODB_CLOUD_KEY", None)
        setup_environment(tmp_path, cloud_key=None)

        assert "ZERODB_CLOUD_KEY" not in os.environ

    def test_download_embedding_model_creates_marker(self, tmp_path):
        """Given first run, marker file should be created"""
        from commands.serve import download_embedding_model, EMBEDDING_MODEL_MARKER

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        download_embedding_model(data_dir)

        assert (data_dir / EMBEDDING_MODEL_MARKER).exists()

    def test_download_embedding_model_skips_if_marker_exists(self, tmp_path):
        """Given marker exists, download should be skipped"""
        from commands.serve import download_embedding_model, EMBEDDING_MODEL_MARKER

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        marker = data_dir / EMBEDDING_MODEL_MARKER
        marker.touch()

        # Should return immediately without error
        download_embedding_model(data_dir)

        assert marker.exists()
