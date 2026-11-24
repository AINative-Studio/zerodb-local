"""
Test suite for zerodb status, logs, and dashboard commands

Story #1132: Status checking, log viewing, and dashboard commands
TDD: Tests written before implementation
"""
import pytest
import subprocess
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from typer.testing import CliRunner


@pytest.fixture
def runner():
    """CLI test runner"""
    return CliRunner()


# ===== Status Command Tests =====

class TestStatusCommand:
    """Test zerodb status command"""

    def test_status_command_exists(self, runner):
        """Should have zerodb status command"""
        from zerodb.commands.status import app

        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "status" in result.stdout.lower()

    def test_status_checks_docker_first(self, runner):
        """Should check if Docker is running before checking services"""
        from zerodb.commands.status import app

        with patch('zerodb.commands.status.check_docker_installed', return_value=False):
            result = runner.invoke(app)

            assert result.exit_code == 1
            assert "docker" in result.stdout.lower()

    def test_status_shows_all_services(self, runner):
        """Should display status of all services"""
        from zerodb.commands.status import app

        # Refs #124: real `docker compose ps --format json` output, not
        # the plain-text format this test previously mocked (which never
        # matched either real Compose generation's actual `ps` output).
        stdout = (
            '{"Service": "postgres", "Name": "zerodb-postgres", '
            '"Status": "Up 5 minutes (healthy)", "State": "running", '
            '"Health": "healthy", "Ports": "0.0.0.0:5432->5432/tcp"}\n'
            '{"Service": "api", "Name": "zerodb-api", '
            '"Status": "Up 5 minutes (healthy)", "State": "running", '
            '"Health": "healthy", "Ports": "0.0.0.0:8000->8000/tcp"}'
        )
        with patch('zerodb.commands.status.check_docker_installed', return_value=True):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout=stdout)

                result = runner.invoke(app)

                assert "postgres" in result.stdout.lower()
                assert "api" in result.stdout.lower()

    def test_status_shows_health_check_results(self, runner):
        """Should show health check status for each service"""
        from zerodb.commands.status import app

        # Refs #124: the `status` command's table path never calls
        # get_service_health() -- it reads Health straight out of
        # get_all_services_status(), which itself comes from parsing
        # `docker compose ps --format json`'s own Health field (this test
        # previously mocked a function the real code path doesn't use,
        # so it was testing nothing).
        stdout = (
            '{"Service": "postgres", "Name": "zerodb-postgres", '
            '"Status": "Up 5 minutes (healthy)", "State": "running", '
            '"Health": "healthy", "Ports": "0.0.0.0:5432->5432/tcp"}\n'
            '{"Service": "qdrant", "Name": "zerodb-qdrant", '
            '"Status": "Up 5 minutes", "State": "starting", '
            '"Health": "starting", "Ports": "0.0.0.0:6333->6333/tcp"}'
        )
        with patch('zerodb.commands.status.check_docker_installed', return_value=True):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout=stdout)

                result = runner.invoke(app)

                assert "healthy" in result.stdout.lower()

    def test_status_shows_port_mappings(self, runner):
        """Should display port mappings for services"""
        from zerodb.commands.status import app

        # Refs #124: get_service_info() was never a real function in
        # status.py -- this test mocked something the implementation
        # doesn't have, so it never actually exercised the real port-
        # display path (parse_docker_compose_output()'s Ports parsing).
        stdout = (
            '{"Service": "postgres", "Name": "zerodb-postgres", '
            '"Status": "Up 5 minutes (healthy)", "State": "running", '
            '"Health": "healthy", "Ports": "0.0.0.0:5432->5432/tcp"}\n'
            '{"Service": "api", "Name": "zerodb-api", '
            '"Status": "Up 5 minutes (healthy)", "State": "running", '
            '"Health": "healthy", "Ports": "0.0.0.0:8000->8000/tcp"}'
        )
        with patch('zerodb.commands.status.check_docker_installed', return_value=True):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout=stdout)

                result = runner.invoke(app)

                assert "5432" in result.stdout
                assert "8000" in result.stdout

    def test_status_handles_no_services_running(self, runner):
        """Should handle case when no services are running"""
        from zerodb.commands.status import app

        with patch('zerodb.commands.status.check_docker_installed', return_value=True):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="")

                result = runner.invoke(app)

                assert "no services" in result.stdout.lower() or "not running" in result.stdout.lower()

    def test_status_shows_service_uptime(self, runner):
        """Should display uptime for running services"""
        from zerodb.commands.status import get_service_uptime

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="Up 2 hours"
            )

            uptime = get_service_uptime("zerodb-postgres")

            assert uptime == "Up 2 hours"

    def test_status_json_output_format(self, runner):
        """Should support JSON output format"""
        from zerodb.commands.status import app

        with patch('zerodb.commands.status.check_docker_installed', return_value=True):
            with patch('zerodb.commands.status.get_all_services_status') as mock_status:
                mock_status.return_value = {
                    'services': [
                        {'name': 'postgres', 'status': 'running', 'health': 'healthy'}
                    ]
                }

                result = runner.invoke(app, ["--json"])

                assert result.exit_code == 0
                # Should output valid JSON
                import json
                try:
                    json.loads(result.stdout)
                except:
                    pytest.fail("Output is not valid JSON")

    def test_status_checks_specific_service(self, runner):
        """Should allow checking status of specific service"""
        from zerodb.commands.status import app

        # Refs #124: the real single-service display path reads
        # status_data['name'] and status_data['port'] (see status()'s
        # `if service:` branch) -- the mocked dict here was missing both,
        # so this never actually exercised what it claimed to test.
        with patch('zerodb.commands.status.check_docker_installed', return_value=True):
            with patch('zerodb.commands.status.get_service_status') as mock_status:
                mock_status.return_value = {
                    'name': 'postgres', 'status': 'running', 'health': 'healthy', 'port': 5432,
                }

                result = runner.invoke(app, ["postgres"])

                assert result.exit_code == 0
                assert "postgres" in result.stdout.lower()

    def test_status_shows_resource_usage(self, runner):
        """Should display CPU and memory usage"""
        from zerodb.commands.status import app

        # Refs #124: get_resource_usage() alone isn't enough -- `status
        # --resources` only reaches the resources table once
        # get_all_services_status() (backed by a real `docker compose ps`
        # subprocess call) returns at least one service; the previous
        # version of this test left that unmocked, so it hit the "No
        # services running" early-return before ever touching resources.
        stdout = (
            '{"Service": "postgres", "Name": "zerodb-postgres", '
            '"Status": "Up 5 minutes (healthy)", "State": "running", '
            '"Health": "healthy", "Ports": "0.0.0.0:5432->5432/tcp"}'
        )
        with patch('zerodb.commands.status.check_docker_installed', return_value=True):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout=stdout)
                with patch('zerodb.commands.status.get_resource_usage') as mock_usage:
                    mock_usage.return_value = {
                        'postgres': {'cpu': '2%', 'memory': '150MB'},
                        'api': {'cpu': '5%', 'memory': '200MB'}
                    }

                    result = runner.invoke(app, ["--resources"])

                    assert "cpu" in result.stdout.lower() or "memory" in result.stdout.lower()


# ===== Logs Command Tests =====

class TestLogsCommand:
    """Test zerodb logs command"""

    def test_logs_command_exists(self, runner):
        """Should have zerodb logs command"""
        from zerodb.commands.logs import app

        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "logs" in result.stdout.lower()

    def test_logs_defaults_to_all_services(self, runner):
        """Should show logs from all services by default"""
        from zerodb.commands.logs import app

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = runner.invoke(app)

            args = mock_run.call_args[0][0]
            assert 'docker-compose' in args
            assert 'logs' in args

    def test_logs_specific_service(self, runner):
        """Should show logs for specific service"""
        from zerodb.commands.logs import app

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = runner.invoke(app, ["postgres"])

            args = mock_run.call_args[0][0]
            assert 'postgres' in args

    def test_logs_follow_mode(self, runner):
        """Should support follow mode (-f)"""
        from zerodb.commands.logs import app

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = runner.invoke(app, ["--follow"])

            args = mock_run.call_args[0][0]
            assert '-f' in args or '--follow' in args

    def test_logs_tail_option(self, runner):
        """Should support tail option to limit output"""
        from zerodb.commands.logs import app

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = runner.invoke(app, ["--tail", "100"])

            args = mock_run.call_args[0][0]
            assert '--tail' in args or '100' in args

    def test_logs_timestamps_option(self, runner):
        """Should support showing timestamps"""
        from zerodb.commands.logs import app

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = runner.invoke(app, ["--timestamps"])

            args = mock_run.call_args[0][0]
            assert '-t' in args or '--timestamps' in args

    def test_logs_handles_keyboard_interrupt(self, runner):
        """Should handle Ctrl+C gracefully"""
        from zerodb.commands.logs import app

        with patch('subprocess.run', side_effect=KeyboardInterrupt):
            result = runner.invoke(app)

            # Should not crash
            assert "stopped" in result.stdout.lower() or result.exit_code in [0, 130]

    def test_logs_handles_service_not_running(self, runner):
        """Should handle case when service is not running"""
        from zerodb.commands.logs import app

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'docker-compose')

            result = runner.invoke(app, ["nonexistent"])

            assert result.exit_code != 0

    def test_logs_since_option(self, runner):
        """Should support filtering logs by time"""
        from zerodb.commands.logs import app

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = runner.invoke(app, ["--since", "1h"])

            args = mock_run.call_args[0][0]
            assert '--since' in args


# ===== Dashboard Command Tests =====

class TestDashboardCommand:
    """Test zerodb dashboard command"""

    def test_dashboard_command_exists(self, runner):
        """Should have zerodb dashboard command"""
        from zerodb.commands.dashboard import app

        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "dashboard" in result.stdout.lower()

    def test_dashboard_checks_if_services_running(self, runner):
        """Should check if services are running before opening"""
        from zerodb.commands.dashboard import app

        with patch('zerodb.commands.dashboard.check_service_running') as mock_check:
            mock_check.return_value = False

            result = runner.invoke(app)

            assert result.exit_code == 1
            assert "not running" in result.stdout.lower()

    def test_dashboard_opens_in_default_browser(self, runner):
        """Should open dashboard in default browser"""
        from zerodb.commands.dashboard import app

        with patch('zerodb.commands.dashboard.check_service_running', return_value=True):
            with patch('webbrowser.open') as mock_open:
                result = runner.invoke(app)

                mock_open.assert_called_once()
                assert 'localhost:3000' in str(mock_open.call_args)

    def test_dashboard_shows_url_if_cannot_open(self, runner):
        """Should show URL if cannot open browser"""
        from zerodb.commands.dashboard import app

        with patch('zerodb.commands.dashboard.check_service_running', return_value=True):
            with patch('webbrowser.open', side_effect=Exception("Cannot open browser")):
                result = runner.invoke(app)

                assert "http://localhost:3000" in result.stdout

    def test_dashboard_custom_port(self, runner):
        """Should support custom port"""
        from zerodb.commands.dashboard import app

        with patch('zerodb.commands.dashboard.check_service_running', return_value=True):
            with patch('webbrowser.open') as mock_open:
                result = runner.invoke(app, ["--port", "8080"])

                assert '8080' in str(mock_open.call_args)

    def test_dashboard_no_browser_flag(self, runner):
        """Should support --no-browser flag to just show URL"""
        from zerodb.commands.dashboard import app

        with patch('zerodb.commands.dashboard.check_service_running', return_value=True):
            with patch('webbrowser.open') as mock_open:
                result = runner.invoke(app, ["--no-browser"])

                mock_open.assert_not_called()
                assert "http://localhost:3000" in result.stdout

    def test_dashboard_opens_specific_services(self, runner):
        """Should support opening specific service dashboards"""
        from zerodb.commands.dashboard import app

        services_urls = {
            'minio': 'http://localhost:9001',
            'qdrant': 'http://localhost:6333/dashboard'
        }

        with patch('zerodb.commands.dashboard.check_service_running', return_value=True):
            with patch('webbrowser.open') as mock_open:
                result = runner.invoke(app, ["minio"])

                assert '9001' in str(mock_open.call_args)


# ===== Helper Functions Tests =====

class TestHelperFunctions:
    """Test helper functions for status/logs/dashboard"""

    def test_get_service_health(self):
        """Should get health status from docker-compose"""
        from zerodb.commands.status import get_service_health

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="healthy"
            )

            health = get_service_health("zerodb-postgres")

            assert health == "healthy"

    def test_get_all_services_status(self):
        """Should get status of all services"""
        from zerodb.commands.status import get_all_services_status

        # Refs #124: real `docker compose ps --format json` output --
        # newline-delimited JSON objects, not plain text. The previous
        # version of this test mocked plain-text stdout that didn't match
        # either Compose generation's real `ps` output, which is exactly
        # how the whitespace-column-parsing bug this now tests against
        # went unnoticed.
        stdout = (
            '{"Service": "postgres", "Name": "zerodb-postgres", '
            '"Status": "Up 5 minutes (healthy)", "State": "running", '
            '"Health": "healthy", "Ports": "0.0.0.0:5432->5432/tcp"}\n'
            '{"Service": "api", "Name": "zerodb-api", '
            '"Status": "Up 5 minutes (healthy)", "State": "running", '
            '"Health": "healthy", "Ports": "0.0.0.0:8000->8000/tcp"}'
        )
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=stdout)

            status = get_all_services_status()

            assert 'postgres' in str(status)
            assert 'api' in str(status)
            assert status['total'] == 2
            # Refs #124: this is the actual regression -- "running" was
            # never 0 of N despite every container really being up and
            # healthy, because the old parser took the Compose V2 IMAGE
            # column for "status" and then substring-matched it for the
            # word "running", which real Compose Status text never
            # contains ("Up X minutes (healthy)").
            assert status['running'] == 2

    def test_parse_docker_compose_output(self):
        """Should parse `docker compose ps --format json` output correctly"""
        from zerodb.commands.status import parse_docker_compose_output

        # One JSON object per line, matching real `docker compose ps
        # --format json` -- captured against a real running stack. Refs #124.
        output = (
            '{"Service": "postgres", "Name": "zerodb-postgres", '
            '"Status": "Up 5 minutes (healthy)", "State": "running", '
            '"Health": "healthy", "Ports": "0.0.0.0:5432->5432/tcp"}\n'
            '{"Service": "api", "Name": "zerodb-api", '
            '"Status": "Up 5 minutes (healthy)", "State": "running", '
            '"Health": "healthy", "Ports": "0.0.0.0:8000->8000/tcp"}'
        )

        result = parse_docker_compose_output(output)

        assert len(result) == 2
        assert result[0]['name'] == 'postgres'
        assert result[0]['port'] == 5432
        assert result[0]['status'] == 'Up 5 minutes (healthy)'
        assert result[0]['health'] == 'healthy'
        assert result[0]['state'] == 'running'

    def test_parse_docker_compose_output_service_without_healthcheck(self):
        """
        A service with no healthcheck defined (e.g. this project's qdrant
        and dashboard services) has an empty Health field in real `docker
        compose ps --format json` output, not "healthy"/"unhealthy" --
        must report 'N/A', not an empty string or a crash. Refs #124.
        """
        from zerodb.commands.status import parse_docker_compose_output

        output = (
            '{"Service": "qdrant", "Name": "zerodb-qdrant", '
            '"Status": "Up 5 minutes", "State": "running", '
            '"Health": "", "Ports": "0.0.0.0:6333->6333/tcp"}'
        )

        result = parse_docker_compose_output(output)

        assert len(result) == 1
        assert result[0]['health'] == 'N/A'
        assert result[0]['state'] == 'running'

    def test_check_service_running(self):
        """Should check if a specific service is running"""
        from zerodb.commands.dashboard import check_service_running

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="running"
            )

            is_running = check_service_running("dashboard")

            assert is_running is True


# ===== Integration Tests =====

@pytest.mark.integration
class TestCommandsIntegration:
    """Integration tests for status/logs/dashboard commands"""

    def test_status_after_init(self, runner, tmp_path):
        """Should be able to check status after init"""
        # This tests the integration between init and status commands
        # In real scenario, services would be running

        # Refs #124: the table-rendering path reads health/port/state off
        # every service dict (see status()'s `for svc in
        # all_status['services']` loop) -- a dict missing them, as this
        # mock previously was, crashes with a KeyError the moment real
        # code (not just this test) hits that gap.
        with patch('zerodb.commands.status.check_docker_installed', return_value=True):
            with patch('zerodb.commands.status.get_all_services_status') as mock_status:
                mock_status.return_value = {
                    'services': [
                        {'name': 'postgres', 'status': 'Up 5 minutes (healthy)',
                         'health': 'healthy', 'port': 5432, 'state': 'running'}
                    ],
                    'total': 1,
                    'running': 1,
                }

                from zerodb.commands.status import app
                result = runner.invoke(app)

                assert result.exit_code == 0

    def test_logs_and_dashboard_require_running_services(self, runner):
        """Should require services to be running"""
        from zerodb.commands.logs import app as logs_app

        with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'docker-compose')):
            result = runner.invoke(logs_app)

            # Should handle error gracefully
            assert result.exit_code != 0
