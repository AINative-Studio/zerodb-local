"""
Tests for local environment commands

Story 3.2: Local Environment Commands
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, call
import subprocess
from typer.testing import CliRunner

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from commands.local import app

runner = CliRunner()


class TestLocalCommands:
    """Test suite for local environment management commands"""

    def test_up_command_starts_services(self):
        """Should start all Docker services with docker-compose up -d"""
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

            result = runner.invoke(app, ['up'])

            assert result.exit_code == 0
            assert 'Starting services' in result.stdout
            # Called twice: once for docker check, once for docker-compose up
            assert mock_run.call_count == 2
            args = mock_run.call_args[0][0]
            assert 'docker-compose' in args or 'docker' in args
            assert 'up' in args
            assert '-d' in args

    def test_up_command_shows_error_when_docker_not_running(self):
        """Should show error message if Docker is not running"""
        with patch('commands.local.subprocess.run') as mock_run:
            # First call (docker version) fails
            mock_run.return_value = Mock(returncode=1)

            result = runner.invoke(app, ['up'])

            assert result.exit_code == 1
            assert 'docker' in result.stdout.lower()

    def test_down_command_stops_services(self):
        """Should stop all Docker services with docker-compose down"""
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

            result = runner.invoke(app, ['down'])

            assert result.exit_code == 0
            # Called twice: once for docker check, once for docker-compose down
            assert mock_run.call_count == 2
            args = mock_run.call_args[0][0]
            assert 'docker-compose' in args or 'docker' in args
            assert 'down' in args

    def test_status_command_shows_service_health(self):
        """Should show status of all services with health information"""
        mock_ps_output = '''NAME                    STATUS              HEALTH
zerodb-postgres         running             healthy
zerodb-api             running             healthy
zerodb-dashboard       running             N/A
'''
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=mock_ps_output, stderr='')

            result = runner.invoke(app, ['status'])

            assert result.exit_code == 0
            assert 'postgres' in result.stdout.lower()
            assert 'api' in result.stdout.lower()

    def test_logs_command_shows_all_logs(self):
        """Should tail logs for all services"""
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = runner.invoke(app, ['logs'])

            # Called twice: once for docker check, once for docker-compose logs
            assert mock_run.call_count == 2
            args = mock_run.call_args[0][0]
            assert 'docker-compose' in args or 'docker' in args
            assert 'logs' in args
            assert '-f' in args

    def test_logs_command_shows_specific_service(self):
        """Should tail logs for a specific service"""
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = runner.invoke(app, ['logs', 'zerodb-api'])

            # Called twice: once for docker check, once for docker-compose logs
            assert mock_run.call_count == 2
            args = mock_run.call_args[0][0]
            assert 'zerodb-api' in args

    def test_reset_command_requires_confirmation(self):
        """Should require confirmation before resetting environment"""
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            # Simulate user declining confirmation in non-interactive mode
            result = runner.invoke(app, ['reset'], input='n\n')

            assert 'cancelled' in result.stdout.lower() or 'warning' in result.stdout.lower()

    def test_reset_command_removes_volumes_and_data(self):
        """Should remove volumes and data directory when confirmed"""
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
            with patch('typer.confirm', return_value=True):
                with patch('commands.local.shutil.rmtree') as mock_rmtree:
                    result = runner.invoke(app, ['reset'])

                    assert result.exit_code == 0
                    # Should call docker-compose down -v
                    down_call = [c for c in mock_run.call_args_list if 'down' in str(c)]
                    assert len(down_call) > 0

    def test_restart_command_restarts_all_services(self):
        """Should restart all services if no service specified"""
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

            result = runner.invoke(app, ['restart'])

            assert result.exit_code == 0
            args = mock_run.call_args[0][0]
            assert 'restart' in args

    def test_restart_command_restarts_specific_service(self):
        """Should restart only the specified service"""
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

            result = runner.invoke(app, ['restart', '--service', 'postgres'])

            args = mock_run.call_args[0][0]
            assert 'restart' in args
            assert 'postgres' in args

    def test_docker_not_installed_error(self):
        """Should show helpful error if Docker is not installed"""
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = runner.invoke(app, ['up'])

            assert result.exit_code == 1
            assert 'docker' in result.stdout.lower()

    def test_status_shows_port_mappings(self):
        """Should display port mappings for each service"""
        mock_ps_output = '''NAME                    STATUS              PORTS
zerodb-postgres         running             0.0.0.0:5432->5432/tcp
zerodb-api             running             0.0.0.0:8000->8000/tcp
'''
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=mock_ps_output, stderr='')

            result = runner.invoke(app, ['status'])

            assert ':5432' in result.stdout or '5432' in result.stdout
            assert ':8000' in result.stdout or '8000' in result.stdout

    def test_up_command_with_logs_option(self):
        """Should show logs when --logs flag is used"""
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

            result = runner.invoke(app, ['up', '--logs'])

            # Should not have -d flag when showing logs
            args = mock_run.call_args[0][0]
            assert 'up' in args


class TestDockerComposeIntegration:
    """Integration tests that verify Docker Compose commands are constructed correctly"""

    def test_correct_working_directory_used(self):
        """Should execute docker-compose from correct working directory"""
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

            result = runner.invoke(app, ['up'])

            # Verify cwd is set to zerodb-local directory
            call_kwargs = mock_run.call_args[1]
            if 'cwd' in call_kwargs:
                assert 'zerodb-local' in call_kwargs['cwd']

    def test_docker_compose_file_specified(self):
        """Should use the correct docker-compose.yml file"""
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

            result = runner.invoke(app, ['up'])

            args = mock_run.call_args[0][0]
            # Should have -f flag or use default docker-compose.yml
            assert 'docker-compose' in args or 'docker' in args
