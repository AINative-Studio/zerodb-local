"""
Test suite for zerodb init command and prerequisites checking

Story #1132: Interactive setup wizard for ZeroLocal
TDD: Tests written before implementation
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
from typer.testing import CliRunner
import socket


@pytest.fixture
def runner():
    """CLI test runner"""
    return CliRunner()


# ===== Prerequisites Tests =====

class TestPrerequisites:
    """Test prerequisite checks for init wizard"""

    def test_check_docker_installed_success(self):
        """Should detect Docker when installed and running"""
        from zerodb.utils.prerequisites import check_docker_installed

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Docker version 24.0.0")

            result = check_docker_installed()

            assert result is True
            mock_run.assert_called_once()

    def test_check_docker_not_installed(self):
        """Should detect when Docker is not installed"""
        from zerodb.utils.prerequisites import check_docker_installed

        with patch('subprocess.run', side_effect=FileNotFoundError):
            result = check_docker_installed()

            assert result is False

    def test_check_docker_not_running(self):
        """Should detect when Docker daemon is not running"""
        from zerodb.utils.prerequisites import check_docker_installed

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="Cannot connect to Docker daemon")

            result = check_docker_installed()

            assert result is False

    def test_check_python_version_supported(self):
        """Should accept Python 3.9+"""
        from zerodb.utils.prerequisites import check_python_version

        with patch('sys.version_info', (3, 9, 0)):
            result = check_python_version()
            assert result['supported'] is True
            assert '3.9.0' in result['version']

        with patch('sys.version_info', (3, 11, 5)):
            result = check_python_version()
            assert result['supported'] is True

    def test_check_python_version_unsupported(self):
        """Should reject Python < 3.9"""
        from zerodb.utils.prerequisites import check_python_version

        with patch('sys.version_info', (3, 8, 0)):
            result = check_python_version()
            assert result['supported'] is False
            assert '3.9+' in result['message']

        with patch('sys.version_info', (2, 7, 0)):
            result = check_python_version()
            assert result['supported'] is False

    def test_check_port_available_success(self):
        """Should detect when port is available"""
        from zerodb.utils.prerequisites import check_port_available

        with patch('socket.socket') as mock_socket:
            mock_socket_instance = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_socket_instance
            mock_socket_instance.connect_ex.return_value = 1  # Port not in use

            result = check_port_available(8000)

            assert result is True

    def test_check_port_in_use(self):
        """Should detect when port is already in use"""
        from zerodb.utils.prerequisites import check_port_available

        with patch('socket.socket') as mock_socket:
            mock_socket_instance = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_socket_instance
            mock_socket_instance.connect_ex.return_value = 0  # Port in use

            result = check_port_available(8000)

            assert result is False

    def test_check_all_ports_available(self):
        """Should check multiple ports at once"""
        from zerodb.utils.prerequisites import check_all_ports

        ports = [8000, 3000, 5432, 6333, 9000]

        with patch('zerodb.utils.prerequisites.check_port_available') as mock_check:
            mock_check.return_value = True

            result = check_all_ports(ports)

            assert result['all_available'] is True
            assert len(result['available']) == 5
            assert len(result['in_use']) == 0

    def test_check_all_ports_some_in_use(self):
        """Should identify which ports are in use"""
        from zerodb.utils.prerequisites import check_all_ports

        ports = [8000, 3000, 5432]

        with patch('zerodb.utils.prerequisites.check_port_available') as mock_check:
            mock_check.side_effect = [True, False, True]

            result = check_all_ports(ports)

            assert result['all_available'] is False
            assert 8000 in result['available']
            assert 3000 in result['in_use']
            assert 5432 in result['available']

    def test_check_disk_space_sufficient(self):
        """Should verify sufficient disk space (10GB minimum)"""
        from zerodb.utils.prerequisites import check_disk_space

        with patch('shutil.disk_usage') as mock_usage:
            mock_usage.return_value = Mock(
                total=100_000_000_000,  # 100GB
                used=50_000_000_000,    # 50GB
                free=50_000_000_000     # 50GB free
            )

            result = check_disk_space()

            assert result['sufficient'] is True
            assert result['free_gb'] >= 10

    def test_check_disk_space_insufficient(self):
        """Should warn when disk space is low"""
        from zerodb.utils.prerequisites import check_disk_space

        with patch('shutil.disk_usage') as mock_usage:
            mock_usage.return_value = Mock(
                total=100_000_000_000,
                used=95_000_000_000,
                free=5_000_000_000  # Only 5GB free
            )

            result = check_disk_space()

            assert result['sufficient'] is False
            assert result['free_gb'] < 10

    def test_check_docker_desktop_running(self):
        """Should verify Docker Desktop is running"""
        from zerodb.utils.prerequisites import check_docker_desktop_running

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="Docker version 24.0.0\nDocker Desktop"
            )

            result = check_docker_desktop_running()

            assert result is True


# ===== Init Wizard Tests =====

class TestInitCommand:
    """Test zerodb init command and setup wizard"""

    def test_init_command_exists(self, runner):
        """Should have zerodb init command"""
        from zerodb.commands.init import app

        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "init" in result.stdout.lower()

    def test_init_checks_prerequisites_first(self, runner):
        """Should check all prerequisites before starting setup"""
        from zerodb.commands.init import app

        with patch('zerodb.commands.init.check_prerequisites') as mock_check:
            mock_check.return_value = {
                'docker': True,
                'python': True,
                'ports': True,
                'disk_space': True
            }
            with patch('zerodb.commands.init.run_setup_wizard'):
                result = runner.invoke(app)

                mock_check.assert_called_once()

    def test_init_fails_if_docker_not_installed(self, runner):
        """Should exit with error if Docker not installed"""
        from zerodb.commands.init import app

        with patch('zerodb.commands.init.check_docker_installed', return_value=False):
            result = runner.invoke(app)

            assert result.exit_code == 1
            assert "docker" in result.stdout.lower()
            assert "install" in result.stdout.lower()

    def test_init_fails_if_ports_in_use(self, runner):
        """Should exit with error if required ports are in use"""
        from zerodb.commands.init import app

        with patch('zerodb.commands.init.check_prerequisites') as mock_check:
            mock_check.return_value = {
                'all_passed': False,
                'docker': True,
                'docker_running': True,
                'python': {'supported': True, 'version': '3.9.0'},
                'ports': {'all_available': False, 'in_use': [8000, 5432]},
                'disk_space': {'sufficient': True, 'free_gb': 50},
                'errors': ['Required ports are in use: 8000, 5432. Please stop services using these ports.'],
                'warnings': []
            }

            result = runner.invoke(app)

            assert result.exit_code == 1
            assert "port" in result.stdout.lower()
            assert "8000" in result.stdout or "5432" in result.stdout

    def test_init_shows_welcome_message(self, runner):
        """Should display welcome message with branding"""
        from zerodb.commands.init import app

        with patch('zerodb.commands.init.check_prerequisites') as mock_check:
            mock_check.return_value = {'all_passed': True}
            with patch('zerodb.commands.init.run_setup_wizard'):
                result = runner.invoke(app)

                assert "ZeroDB" in result.stdout
                assert "Setup Wizard" in result.stdout

    def test_init_prompts_for_configuration(self, runner):
        """Should prompt user for configuration options"""
        from zerodb.commands.init import app

        with patch('zerodb.commands.init.check_prerequisites') as mock_check:
            mock_check.return_value = {'all_passed': True}
            with patch('typer.prompt') as mock_prompt:
                mock_prompt.side_effect = [
                    "my-project",  # Project name
                    "local",       # Environment
                    "y"            # Confirm
                ]
                with patch('zerodb.commands.init.create_environment'):
                    result = runner.invoke(app)

                    assert mock_prompt.call_count >= 2

    def test_init_creates_data_directories(self, runner, tmp_path):
        """Should create required data directories"""
        from zerodb.commands.init import create_data_directories

        project_root = tmp_path / "zerodb-local"
        project_root.mkdir()

        create_data_directories(project_root)

        assert (project_root / "data" / "postgres").exists()
        assert (project_root / "data" / "qdrant").exists()
        assert (project_root / "data" / "minio").exists()
        assert (project_root / "data" / "redpanda").exists()
        assert (project_root / "data" / "embeddings" / "models").exists()

    def test_init_creates_env_file(self, runner, tmp_path):
        """Should create .env file with configuration"""
        from zerodb.commands.init import create_env_file

        config = {
            'project_name': 'my-project',
            'postgres_db': 'zerodb_local',
            'postgres_user': 'zerodb',
            'postgres_password': 'localpass'
        }

        env_path = tmp_path / ".env"
        create_env_file(env_path, config)

        assert env_path.exists()
        content = env_path.read_text()
        assert "POSTGRES_DB=zerodb_local" in content
        assert "POSTGRES_USER=zerodb" in content

    def test_init_starts_services_with_docker_compose(self, runner):
        """Should start Docker services after configuration"""
        from zerodb.commands.init import app

        with patch('zerodb.commands.init.check_prerequisites') as mock_check:
            mock_check.return_value = {'all_passed': True}
            with patch('zerodb.commands.init.run_setup_wizard'):
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = Mock(returncode=0)

                    result = runner.invoke(app, ["--start-services"])

                    # Should call docker-compose up
                    assert any('docker-compose' in str(call) for call in mock_run.call_args_list)

    def test_init_shows_progress_indicators(self, runner):
        """Should show progress during setup"""
        from zerodb.commands.init import app

        with patch('zerodb.commands.init.check_prerequisites') as mock_check:
            mock_check.return_value = {'all_passed': True}
            with patch('zerodb.commands.init.run_setup_wizard'):
                result = runner.invoke(app)

                # Should show progress steps
                assert "Checking prerequisites" in result.stdout or "✓" in result.stdout

    def test_init_skip_confirmation_with_flag(self, runner):
        """Should skip confirmation with --yes flag"""
        from zerodb.commands.init import app

        with patch('zerodb.commands.init.check_prerequisites') as mock_check:
            mock_check.return_value = {'all_passed': True}
            with patch('zerodb.commands.init.run_setup_wizard') as mock_wizard:
                result = runner.invoke(app, ["--yes"])

                # Should not prompt for confirmation
                mock_wizard.assert_called_once()

    def test_init_handles_keyboard_interrupt(self, runner):
        """Should handle Ctrl+C gracefully"""
        from zerodb.commands.init import app

        with patch('zerodb.commands.init.run_setup_wizard', side_effect=KeyboardInterrupt):
            result = runner.invoke(app)

            assert "cancelled" in result.stdout.lower() or result.exit_code != 0

    def test_init_shows_next_steps_on_success(self, runner):
        """Should display next steps after successful setup"""
        from zerodb.commands.init import app

        with patch('zerodb.commands.init.check_prerequisites') as mock_check:
            mock_check.return_value = {'all_passed': True}
            with patch('zerodb.commands.init.run_setup_wizard'):
                result = runner.invoke(app)

                assert "zerodb status" in result.stdout or "next" in result.stdout.lower()

    def test_init_shows_helpful_error_for_docker_not_running(self, runner):
        """Should show helpful error message when Docker daemon not running"""
        from zerodb.commands.init import app

        with patch('zerodb.commands.init.check_docker_installed', return_value=True):
            with patch('zerodb.commands.init.check_docker_desktop_running', return_value=False):
                result = runner.invoke(app)

                assert result.exit_code == 1
                assert "Docker Desktop" in result.stdout
                assert "not running" in result.stdout.lower()

    def test_init_validates_disk_space_before_proceeding(self, runner):
        """Should warn if disk space is insufficient"""
        from zerodb.commands.init import app

        with patch('zerodb.commands.init.check_docker_installed', return_value=True):
            with patch('zerodb.commands.init.check_disk_space') as mock_disk:
                mock_disk.return_value = {'sufficient': False, 'free_gb': 3}

                result = runner.invoke(app)

                assert "disk space" in result.stdout.lower()
                assert result.exit_code == 1 or "warning" in result.stdout.lower()

    def test_init_idempotent_can_run_multiple_times(self, runner, tmp_path):
        """Should be idempotent - can run multiple times safely"""
        from zerodb.commands.init import create_data_directories

        project_root = tmp_path / "zerodb-local"
        project_root.mkdir()

        # Run twice
        create_data_directories(project_root)
        create_data_directories(project_root)

        # Should still work without errors
        assert (project_root / "data" / "postgres").exists()


# ===== Configuration Wizard Tests =====

class TestConfigurationWizard:
    """Test interactive configuration wizard"""

    def test_wizard_provides_sensible_defaults(self):
        """Should provide sensible defaults for all configuration"""
        from zerodb.commands.init import get_default_config

        config = get_default_config()

        assert config['postgres_db'] == 'zerodb_local'
        assert config['postgres_user'] == 'zerodb'
        assert 'postgres_password' in config
        assert config['minio_access_key'] == 'minioadmin'

    def test_wizard_allows_custom_values(self, runner):
        """Should allow user to override defaults"""
        from zerodb.commands.init import app

        with patch('zerodb.commands.init.check_prerequisites') as mock_check:
            mock_check.return_value = {'all_passed': True}
            with patch('typer.prompt') as mock_prompt:
                mock_prompt.side_effect = [
                    "custom_db",     # Custom database name
                    "custom_user",   # Custom user
                    "y"
                ]
                with patch('zerodb.commands.init.create_environment') as mock_create:
                    result = runner.invoke(app, ["--interactive"])

                    # Should have called prompt
                    assert mock_prompt.call_count >= 2

    def test_wizard_validates_input(self):
        """Should validate user input"""
        from zerodb.commands.init import validate_project_name

        # Valid names
        assert validate_project_name("my-project") is True
        assert validate_project_name("project_123") is True

        # Invalid names
        assert validate_project_name("") is False
        assert validate_project_name("my project") is False  # spaces
        assert validate_project_name("my@project") is False  # special chars

    def test_wizard_shows_configuration_summary(self, runner):
        """Should show configuration summary before applying"""
        from zerodb.commands.init import app

        with patch('zerodb.commands.init.check_prerequisites') as mock_check:
            mock_check.return_value = {'all_passed': True}
            with patch('zerodb.commands.init.run_setup_wizard'):
                result = runner.invoke(app)

                # Should display configuration
                assert "Configuration" in result.stdout or "Settings" in result.stdout


# ===== Service Startup Tests =====

class TestServiceStartup:
    """Test service startup and health checking"""

    def test_starts_services_in_correct_order(self):
        """Should start services with proper dependency order"""
        from zerodb.commands.init import start_services

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            start_services(Path("/tmp/zerodb-local"))

            # Should use docker-compose up
            args = mock_run.call_args[0][0]
            assert 'docker-compose' in args
            assert 'up' in args
            assert '-d' in args

    def test_waits_for_services_to_be_healthy(self):
        """Should wait for services to report healthy"""
        from zerodb.commands.init import wait_for_services_healthy

        with patch('requests.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {'status': 'healthy'}
            )

            result = wait_for_services_healthy(timeout=10)

            assert result is True

    def test_timeout_if_services_dont_start(self):
        """Should timeout if services don't become healthy"""
        from zerodb.commands.init import wait_for_services_healthy

        with patch('requests.get', side_effect=Exception("Connection refused")):
            result = wait_for_services_healthy(timeout=1)

            assert result is False

    def test_shows_real_time_status_during_startup(self, runner):
        """Should show real-time status of services starting up"""
        from zerodb.commands.init import app

        with patch('zerodb.commands.init.check_prerequisites') as mock_check:
            mock_check.return_value = {'all_passed': True}
            with patch('zerodb.commands.init.start_services'):
                with patch('zerodb.commands.init.monitor_startup') as mock_monitor:
                    result = runner.invoke(app, ["--start-services"])

                    # Should monitor startup
                    mock_monitor.assert_called_once()


# ===== Error Handling Tests =====

class TestErrorHandling:
    """Test error handling in init wizard"""

    def test_handles_docker_compose_failure(self, runner):
        """Should handle docker-compose command failures gracefully"""
        from zerodb.commands.init import start_services

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'docker-compose')

            with pytest.raises(Exception) as exc_info:
                start_services(Path("/tmp/zerodb-local"))

            assert "docker" in str(exc_info.value).lower()

    def test_handles_permission_errors(self, runner, tmp_path):
        """Should handle permission errors when creating directories"""
        from zerodb.commands.init import create_data_directories

        project_root = tmp_path / "zerodb-local"
        project_root.mkdir()
        project_root.chmod(0o444)  # Read-only

        with pytest.raises(PermissionError):
            create_data_directories(project_root)

    def test_shows_troubleshooting_link_on_error(self, runner):
        """Should show troubleshooting documentation link on errors"""
        from zerodb.commands.init import app

        with patch('zerodb.commands.init.check_docker_installed', return_value=False):
            result = runner.invoke(app)

            assert "http" in result.stdout or "docs" in result.stdout.lower()


# ===== Integration Tests =====

@pytest.mark.integration
class TestInitIntegration:
    """Integration tests for init command (requires mocks)"""

    def test_full_init_flow_with_defaults(self, runner, tmp_path):
        """Should complete full init flow with default settings"""
        from zerodb.commands.init import app

        with patch('zerodb.commands.init.check_prerequisites') as mock_check:
            mock_check.return_value = {'all_passed': True}
            with patch('zerodb.commands.init.PROJECT_ROOT', tmp_path):
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = Mock(returncode=0)

                    result = runner.invoke(app, ["--yes"])

                    assert result.exit_code == 0
                    assert (tmp_path / "data").exists()

    def test_init_and_status_commands_work_together(self, runner, tmp_path):
        """Should be able to run status command after init"""
        from zerodb.commands.init import app as init_app

        with patch('zerodb.commands.init.check_prerequisites') as mock_check:
            mock_check.return_value = {'all_passed': True}
            with patch('zerodb.commands.init.PROJECT_ROOT', tmp_path):
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = Mock(returncode=0)

                    # Run init
                    result = runner.invoke(init_app, ["--yes"])
                    assert result.exit_code == 0

                    # Should be able to check status
                    # This will be tested when status command is implemented
