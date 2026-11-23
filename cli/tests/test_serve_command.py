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

    def test_default_host_is_this_machine_only(self):
        """Given no --host flag, the server is only reachable from this machine.

        Local mode has no sign-in, so listening on all interfaces by default
        would expose every project to anyone on the same network.
        """
        from commands.serve import DEFAULT_HOST

        assert DEFAULT_HOST == "127.0.0.1"

    def test_default_data_dir_is_home_zerodb(self):
        """Given no --data-dir flag, the default should be ~/.zerodb/data/"""
        from commands.serve import DEFAULT_DATA_DIR

        expected = Path.home() / ".zerodb" / "data"
        assert DEFAULT_DATA_DIR == expected

    @patch("commands.serve.uvicorn")
    def test_serve_calls_uvicorn_with_defaults(self, mock_uvicorn, runner, serve_app, tmp_data_dir):
        """Given default args, uvicorn.run should be called with port 8000.

        Refs #75: the real FastAPI app lives in api/main.py (package "api",
        not "app" -- no "app" package exists anywhere in this repo or the
        installed distribution), so the module string must be "main:app"
        (matching tests/test_lite_mode_crud.py's lite_server fixture, which
        runs the same server by cwd-ing into api/ first -- api/main.py's own
        sibling-relative imports, e.g. "from health import ...", require it).
        """
        result = runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir)])

        mock_uvicorn.run.assert_called_once_with(
            "main:app",
            host="127.0.0.1",
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
        """Given serve runs, uvicorn should load main:app from the api/
        working directory -- see #75: there is no "app" package."""
        result = runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir)])

        args, kwargs = mock_uvicorn.run.call_args
        assert args[0] == "main:app"

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


# ===== Network exposure warning =====

class TestExposureWarning:
    """Scenario: User opts into listening on the network"""

    def test_no_warning_on_loopback(self):
        from commands.serve import exposure_warning

        assert exposure_warning("127.0.0.1", key_set=False) is None
        assert exposure_warning("localhost", key_set=False) is None
        assert exposure_warning("::1", key_set=False) is None

    def test_warns_when_exposed_without_a_key(self):
        from commands.serve import exposure_warning

        msg = exposure_warning("0.0.0.0", key_set=False)
        assert msg is not None
        assert "ZERODB_LOCAL_API_KEY" in msg

    def test_quiet_when_exposed_with_a_key(self):
        from commands.serve import exposure_warning

        assert exposure_warning("0.0.0.0", key_set=True) is None


# ===== Real server startup (no mocks) =====

class TestServeStartsRealServer:
    """Refs #75: `zerodb serve` crashed immediately with
    `ModuleNotFoundError: No module named 'app'` for every user following
    the README's documented quickstart -- uvicorn.run("app.main:app", ...)
    pointed at a package that doesn't exist anywhere in this repo or the
    installed distribution. The mocked uvicorn tests above caught the
    *call arguments* regressing, but only a real subprocess that actually
    imports and serves the app proves the command itself works end to end.
    """

    def test_serve_command_actually_starts_and_serves_health(self, tmp_path):
        import shutil
        import socket
        import subprocess
        import sys
        import time

        import httpx

        def _free_port() -> int:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", 0))
                return s.getsockname()[1]

        # Invoke the real installed `zerodb` console script (the exact
        # command the README tells users to run), not `python -m
        # zerodb_local.cli`: that module defines the Typer `app` but has no
        # `if __name__ == "__main__": app()` guard, so running it as `-m`
        # merely imports it and exits 0 without invoking anything.
        zerodb_bin = Path(sys.executable).parent / "zerodb"
        if not zerodb_bin.exists():
            zerodb_bin = shutil.which("zerodb")
            if not zerodb_bin:
                pytest.skip("zerodb console script not found on PATH")

        port = _free_port()
        data_dir = tmp_path / "zerodb_serve_data"
        cli_dir = Path(__file__).parent.parent

        env = dict(os.environ)
        env.pop("DATABASE_URL", None)

        proc = subprocess.Popen(
            [
                str(zerodb_bin), "serve",
                "--port", str(port),
                "--data-dir", str(data_dir),
            ],
            cwd=str(cli_dir.parent),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        base_url = f"http://127.0.0.1:{port}"
        try:
            for _ in range(50):
                if proc.poll() is not None:
                    output = proc.stdout.read()
                    pytest.fail(
                        f"zerodb serve exited early with code "
                        f"{proc.returncode}:\n{output}"
                    )
                try:
                    resp = httpx.get(f"{base_url}/health", timeout=1)
                    if resp.status_code == 200:
                        assert resp.json()["backend"] == "lite"
                        return
                except httpx.ConnectError:
                    time.sleep(0.2)
            pytest.fail("zerodb serve did not start in time")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


class TestWatchFlagWiring:
    """Refs #105: --watch should route through watch_server() instead of
    calling uvicorn directly, so the server auto-restarts on a crash."""

    @patch("commands.serve.watch_server")
    @patch("commands.serve._run_server")
    def test_watch_flag_calls_watch_server(
        self, mock_run_server, mock_watch_server, runner, serve_app, tmp_data_dir
    ):
        runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir), "--watch"])
        mock_watch_server.assert_called_once()
        mock_run_server.assert_not_called()

    @patch("commands.serve.watch_server")
    @patch("commands.serve._run_server")
    def test_no_watch_flag_calls_run_server_directly(
        self, mock_run_server, mock_watch_server, runner, serve_app, tmp_data_dir
    ):
        runner.invoke(serve_app, ["--data-dir", str(tmp_data_dir)])
        mock_run_server.assert_called_once()
        mock_watch_server.assert_not_called()


class TestWatchServerRestartLogic:
    """Refs #105: unit-level coverage of watch_server's restart/backoff/
    give-up decisions, using a fake multiprocessing.Process so these run
    fast and don't need a real server. The real-crash-recovery behavior
    is additionally proven end to end in TestWatchServerRealCrashRecovery
    below, against the actual server process."""

    def _fake_process_class(self, exitcodes):
        """A stand-in for multiprocessing.Process whose .join() immediately
        "completes" with each exitcode in turn (one instance per restart
        attempt, matching watch_server's one-Process-per-loop-iteration
        shape)."""
        exitcodes_iter = iter(exitcodes)

        class _FakeProcess:
            def __init__(self, target=None, args=None, daemon=None):
                self.exitcode = None

            def start(self):
                self.exitcode = next(exitcodes_iter)

            def join(self, timeout=None):
                pass

            def is_alive(self):
                return False

            def terminate(self):
                pass

            def kill(self):
                pass

        return _FakeProcess

    @patch("commands.serve.time.sleep")
    @patch("commands.serve.multiprocessing.Process")
    def test_clean_exit_does_not_restart(self, mock_process_cls, mock_sleep):
        from commands.serve import watch_server

        mock_process_cls.side_effect = self._fake_process_class([0])
        watch_server("127.0.0.1", 8000, False)

        assert mock_process_cls.call_count == 1
        mock_sleep.assert_not_called()

    @patch("commands.serve.time.sleep")
    @patch("commands.serve.multiprocessing.Process")
    def test_crash_then_clean_exit_restarts_once(self, mock_process_cls, mock_sleep):
        from commands.serve import watch_server

        mock_process_cls.side_effect = self._fake_process_class([1, 0])
        watch_server("127.0.0.1", 8000, False)

        assert mock_process_cls.call_count == 2
        mock_sleep.assert_called_once()

    @patch("commands.serve.time.sleep")
    @patch("commands.serve.multiprocessing.Process")
    def test_persistent_crash_loop_gives_up_instead_of_looping_forever(
        self, mock_process_cls, mock_sleep
    ):
        import typer
        from commands.serve import watch_server, _CRASH_LOOP_MAX_RESTARTS

        # Always crash -- watch_server must eventually stop retrying
        # rather than restart forever.
        mock_process_cls.side_effect = self._fake_process_class(
            [1] * (_CRASH_LOOP_MAX_RESTARTS + 5)
        )

        with pytest.raises(typer.Exit) as exc_info:
            watch_server("127.0.0.1", 8000, False)

        assert exc_info.value.exit_code == 1
        # Gave up at or just past the configured threshold, not after
        # exhausting every crash in the side_effect list.
        assert mock_process_cls.call_count <= _CRASH_LOOP_MAX_RESTARTS + 1

    @patch("commands.serve.time.sleep")
    @patch("commands.serve.multiprocessing.Process")
    def test_backoff_delay_increases_between_restarts(
        self, mock_process_cls, mock_sleep
    ):
        from commands.serve import watch_server, _RESTART_BACKOFF_SECONDS

        mock_process_cls.side_effect = self._fake_process_class([1, 1, 1, 0])
        watch_server("127.0.0.1", 8000, False)

        delays = [c.args[0] for c in mock_sleep.call_args_list]
        assert delays == _RESTART_BACKOFF_SECONDS[:3]


class TestWatchServerRealCrashRecovery:
    """Refs #105: end-to-end proof that `zerodb serve --watch` actually
    restarts after a real crash, not just that the mocked restart logic
    is internally consistent. Mirrors TestServeStartsRealServer's use of
    a real subprocess rather than in-process mocks, for the same reason:
    a real crash caused by a real OS-level process kill is the only thing
    that proves this end to end."""

    def test_server_recovers_after_the_child_process_is_killed(self, tmp_path):
        import shutil
        import signal
        import socket
        import subprocess
        import sys
        import time

        import httpx

        def _pid_listening_on(port: int):
            """Find the PID with a listening socket on `port`, via lsof --
            avoids adding psutil as a dependency just for this one test."""
            result = subprocess.run(
                ["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"],
                capture_output=True,
                text=True,
            )
            pids = [int(p) for p in result.stdout.split()]
            return pids[0] if pids else None

        def _free_port() -> int:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", 0))
                return s.getsockname()[1]

        zerodb_bin = Path(sys.executable).parent / "zerodb"
        if not zerodb_bin.exists():
            zerodb_bin = shutil.which("zerodb")
            if not zerodb_bin:
                pytest.skip("zerodb console script not found on PATH")

        port = _free_port()
        data_dir = tmp_path / "zerodb_watch_data"
        cli_dir = Path(__file__).parent.parent

        env = dict(os.environ)
        env.pop("DATABASE_URL", None)

        supervisor = subprocess.Popen(
            [
                str(zerodb_bin), "serve",
                "--port", str(port),
                "--data-dir", str(data_dir),
                "--watch",
            ],
            cwd=str(cli_dir.parent),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        base_url = f"http://127.0.0.1:{port}"
        try:
            for _ in range(50):
                if supervisor.poll() is not None:
                    pytest.fail(
                        f"supervisor exited early with code "
                        f"{supervisor.returncode}:\n{supervisor.stdout.read()}"
                    )
                try:
                    if httpx.get(f"{base_url}/health", timeout=1).status_code == 200:
                        break
                except httpx.ConnectError:
                    time.sleep(0.2)
            else:
                pytest.fail("server did not start in time")

            # Hard-kill whichever process is actually listening on the
            # port -- the uvicorn child, not the supervisor -- the same
            # way an OOM kill or an unhandled crash would take down only
            # the server. lsof avoids adding psutil as a dependency just
            # for this one test.
            child_pid = _pid_listening_on(port)
            assert child_pid is not None, "expected a process listening on the port"
            assert child_pid != supervisor.pid, (
                "expected --watch to run the server in a child process, "
                "not the supervisor itself"
            )
            os.kill(child_pid, signal.SIGKILL)

            for _ in range(50):
                try:
                    if httpx.get(f"{base_url}/health", timeout=1).status_code == 200:
                        return
                except httpx.TransportError:
                    # Polling across the kill -> restart transition: the
                    # old socket can refuse (ConnectError), reset mid-read
                    # if the kill lands between accept and response
                    # (ReadError), or momentarily accept-then-drop while
                    # the new child is still starting up -- all expected,
                    # not just a plain connection refusal.
                    time.sleep(0.2)
            pytest.fail("server did not come back up after the child was killed")
        finally:
            supervisor.terminate()
            try:
                supervisor.wait(timeout=10)
            except subprocess.TimeoutExpired:
                supervisor.kill()
                supervisor.wait(timeout=5)
