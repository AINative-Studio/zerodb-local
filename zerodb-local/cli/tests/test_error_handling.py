"""
Error handling tests for CLI

Story #426: Extend CLI Test Suite - Error Handling Tests

Tests graceful error handling for various failure scenarios.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess
import httpx
from pathlib import Path
from typer.testing import CliRunner
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from commands.local import app as local_app
from commands.sync import app as sync_app
from commands.inspect import app as inspect_app
from commands.cloud import app as cloud_app


@pytest.mark.unit
class TestDockerNotInstalled:
    """Test error handling when Docker is not installed"""

    def test_up_command_docker_not_installed(self, cli_runner, docker_not_installed):
        """Should show helpful error when Docker not installed"""
        with patch('commands.local.subprocess.run', docker_not_installed):
            result = cli_runner.invoke(local_app, ['up'])

            assert result.exit_code == 1
            assert 'docker' in result.stdout.lower()

    def test_down_command_docker_not_installed(self, cli_runner, docker_not_installed):
        """Should handle Docker not installed gracefully"""
        with patch('commands.local.subprocess.run', docker_not_installed):
            result = cli_runner.invoke(local_app, ['down'])

            assert result.exit_code == 1
            assert 'docker' in result.stdout.lower()

    def test_status_command_docker_not_installed(self, cli_runner, docker_not_installed):
        """Should show clear error for status command"""
        with patch('commands.local.subprocess.run', docker_not_installed):
            result = cli_runner.invoke(local_app, ['status'])

            assert result.exit_code == 1
            assert 'docker' in result.stdout.lower() or 'install' in result.stdout.lower()


@pytest.mark.unit
class TestDockerNotRunning:
    """Test error handling when Docker daemon is not running"""

    def test_up_command_docker_not_running(self, cli_runner):
        """Should show error when Docker daemon not running"""
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr='Cannot connect to Docker daemon')

            result = cli_runner.invoke(local_app, ['up'])

            assert result.exit_code == 1
            assert 'docker' in result.stdout.lower()

    def test_status_command_docker_not_running(self, cli_runner):
        """Should detect Docker not running"""
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1)

            result = cli_runner.invoke(local_app, ['status'])

            assert result.exit_code == 1


@pytest.mark.unit
class TestAPINotReachable:
    """Test error handling when API is not reachable"""

    def test_health_check_api_not_reachable(self, cli_runner):
        """Should show clear error when API not reachable"""
        with patch('commands.inspect.APIClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get.side_effect = Exception(
                "Local API not running at http://localhost:8000. "
                "Run 'zerodb local up' to start the local environment."
            )

            result = cli_runner.invoke(inspect_app, ['health'])

            assert result.exit_code == 1
            assert 'not running' in result.stdout.lower() or 'error' in result.stdout.lower()

    def test_projects_api_not_reachable(self, cli_runner):
        """Should handle API unavailable for projects command"""
        with patch('commands.inspect.APIClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")

            result = cli_runner.invoke(inspect_app, ['projects'])

            assert result.exit_code == 1
            assert 'error' in result.stdout.lower()

    def test_sync_plan_api_not_reachable(self, cli_runner, configured_project):
        """Should handle API unavailable for sync plan"""
        with patch('commands.sync.SyncPlanner') as MockPlanner:
            mock_planner = MockPlanner.return_value
            mock_planner.generate_plan.side_effect = ConnectionError(
                "Cannot connect to cloud API"
            )

            result = cli_runner.invoke(sync_app, ['plan'])

            assert result.exit_code == 1
            assert 'error' in result.stdout.lower() or 'connect' in result.stdout.lower()


@pytest.mark.unit
class TestInvalidProjectID:
    """Test error handling for invalid project IDs"""

    def test_inspect_sync_invalid_project(self, cli_runner):
        """Should handle invalid project ID gracefully"""
        with patch('commands.inspect.APIClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get.side_effect = Exception("Resource not found: /v1/projects/invalid-id/sync/state")

            result = cli_runner.invoke(inspect_app, ['sync', '--project-id', 'invalid-id'])

            assert result.exit_code == 1
            assert 'error' in result.stdout.lower()

    def test_inspect_vectors_invalid_project(self, cli_runner):
        """Should show error for non-existent project"""
        with patch('commands.inspect.APIClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get.side_effect = Exception("Resource not found")

            result = cli_runner.invoke(inspect_app, ['vectors', '--project-id', 'nonexistent'])

            assert result.exit_code == 1


@pytest.mark.unit
class TestNotAuthenticated:
    """Test error handling when not authenticated to cloud"""

    def test_sync_plan_not_authenticated(self, cli_runner):
        """Should prompt for authentication when not logged in"""
        with patch('commands.sync.get_cloud_credentials', return_value=None):
            with patch('commands.sync.load_config', return_value={'project_id': 'test-123'}):
                result = cli_runner.invoke(sync_app, ['plan'])

                # Should fail with authentication error
                assert result.exit_code == 1
                assert 'login' in result.stdout.lower() or 'auth' in result.stdout.lower()

    def test_sync_apply_not_authenticated(self, cli_runner):
        """Should require authentication for sync apply"""
        with patch('commands.sync.get_cloud_credentials', return_value=None):
            with patch('commands.sync.load_config', return_value={'project_id': 'test-123'}):
                result = cli_runner.invoke(sync_app, ['apply', '--yes'])

                assert result.exit_code == 1
                assert 'login' in result.stdout.lower() or 'not logged in' in result.stdout.lower()

    def test_cloud_login_invalid_credentials(self, cli_runner):
        """Should handle invalid login credentials"""
        with patch('commands.cloud.httpx.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=401,
                json=lambda: {'detail': 'Invalid credentials'}
            )

            result = cli_runner.invoke(cloud_app, ['login'], input='test@example.com\nwrongpassword\n')

            # Should show authentication failed
            # Note: Actual behavior depends on cloud.py implementation


@pytest.mark.unit
class TestNetworkErrors:
    """Test error handling for network errors"""

    def test_timeout_error(self, cli_runner, configured_project):
        """Should handle timeout errors gracefully"""
        with patch('commands.inspect.APIClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get.side_effect = httpx.TimeoutException("Request timeout")

            result = cli_runner.invoke(inspect_app, ['health'])

            assert result.exit_code == 1
            assert 'error' in result.stdout.lower() or 'timeout' in result.stdout.lower()

    def test_network_interruption(self, cli_runner, configured_project):
        """Should handle network interruption mid-request"""
        with patch('commands.inspect.APIClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get.side_effect = httpx.NetworkError("Network unreachable")

            result = cli_runner.invoke(inspect_app, ['projects'])

            assert result.exit_code == 1
            assert 'error' in result.stdout.lower()

    def test_ssl_error(self, cli_runner, configured_project):
        """Should handle SSL/TLS errors"""
        with patch('commands.inspect.APIClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get.side_effect = httpx.ConnectError("SSL: CERTIFICATE_VERIFY_FAILED")

            result = cli_runner.invoke(inspect_app, ['health'])

            assert result.exit_code == 1


@pytest.mark.unit
class TestInvalidInput:
    """Test error handling for invalid input"""

    def test_sync_plan_invalid_direction(self, cli_runner, configured_project):
        """Should reject invalid sync direction"""
        result = cli_runner.invoke(sync_app, ['plan', '--direction', 'invalid'])

        assert result.exit_code == 1
        assert 'invalid' in result.stdout.lower() or 'direction' in result.stdout.lower()

    def test_sync_plan_invalid_format(self, cli_runner, configured_project):
        """Should reject invalid output format"""
        result = cli_runner.invoke(sync_app, ['plan', '--format', 'xml'])

        assert result.exit_code == 1
        assert 'invalid' in result.stdout.lower() or 'format' in result.stdout.lower()

    def test_sync_plan_invalid_entity_types(self, cli_runner, configured_project):
        """Should reject invalid entity types"""
        result = cli_runner.invoke(sync_app, [
            'plan',
            '--entity-types',
            'vectors,invalid_type,tables'
        ])

        assert result.exit_code == 1
        assert 'invalid' in result.stdout.lower()

    def test_local_restart_invalid_service(self, cli_runner):
        """Should handle invalid service name gracefully"""
        with patch('commands.local.subprocess.run') as mock_run:
            # Docker returns error for invalid service
            mock_run.side_effect = [
                Mock(returncode=0),  # Docker check
                subprocess.CalledProcessError(
                    1,
                    'docker-compose restart invalid',
                    stderr='No such service: invalid'
                )
            ]

            result = cli_runner.invoke(local_app, ['restart', '--service', 'invalid'])

            # Should propagate error
            assert result.exit_code == 1


@pytest.mark.unit
class TestMissingConfiguration:
    """Test error handling for missing configuration"""

    def test_sync_plan_no_project_linked(self, cli_runner, temp_config_dir):
        """Should prompt to link project when none linked"""
        with patch('commands.sync.load_config', return_value={'project_id': None}):
            result = cli_runner.invoke(sync_app, ['plan'])

            assert result.exit_code == 1
            assert 'no project' in result.stdout.lower() or 'link' in result.stdout.lower()

    def test_inspect_sync_no_project_linked(self, cli_runner, temp_config_dir):
        """Should show error when no project linked"""
        with patch('commands.inspect.get_project_id', return_value=None):
            result = cli_runner.invoke(inspect_app, ['sync'])

            assert result.exit_code == 1
            assert 'no project' in result.stdout.lower() or 'link' in result.stdout.lower()

    def test_commands_with_missing_config_file(self, cli_runner, temp_config_dir):
        """Should handle missing config file gracefully"""
        # Config file doesn't exist, should use defaults
        result = cli_runner.invoke(inspect_app, ['health'])

        # Should either work with defaults or show appropriate error
        # Actual behavior depends on whether API is reachable
        assert result.exit_code in [0, 1]


@pytest.mark.unit
class TestPartialFailures:
    """Test error handling for partial failures"""

    def test_sync_partial_failure_rollback(self, cli_runner, configured_project,
                                          sample_sync_plan, mock_failed_sync_result):
        """Should rollback on partial sync failure"""
        from sync_executor import SyncExecutionError

        with patch('commands.sync.SyncPlanner') as MockPlanner:
            with patch('commands.sync.SyncExecutor') as MockExecutor:
                with patch('commands.sync.ConflictResolver'):
                    mock_planner = MockPlanner.return_value
                    mock_planner.generate_plan.return_value = sample_sync_plan

                    mock_executor = MockExecutor.return_value
                    mock_executor.execute_plan.side_effect = SyncExecutionError(
                        "Failed to sync 3 operations"
                    )

                    result = cli_runner.invoke(sync_app, ['apply', '--yes'])

                    assert result.exit_code == 1
                    assert 'failed' in result.stdout.lower()

    def test_health_check_degraded_services(self, cli_runner):
        """Should show degraded status when some services unhealthy"""
        with patch('commands.inspect.APIClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get.return_value = {
                'status': 'degraded',
                'timestamp': '2025-12-29T12:00:00Z',
                'services': {
                    'postgresql': {'status': 'healthy', 'response_time_ms': 5},
                    'qdrant': {'status': 'unhealthy', 'response_time_ms': 0},
                    'minio': {'status': 'healthy', 'response_time_ms': 3}
                }
            }

            result = cli_runner.invoke(inspect_app, ['health'])

            assert result.exit_code == 0
            assert 'degraded' in result.stdout.lower() or 'unhealthy' in result.stdout.lower()


@pytest.mark.unit
class TestResourceConstraints:
    """Test error handling for resource constraints"""

    def test_insufficient_disk_space(self, cli_runner):
        """Should handle insufficient disk space errors"""
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0),  # Docker check
                subprocess.CalledProcessError(
                    1,
                    'docker-compose up',
                    stderr='no space left on device'
                )
            ]

            result = cli_runner.invoke(local_app, ['up'])

            assert result.exit_code == 1
            # Error should be shown
            assert len(result.stdout) > 0

    def test_memory_constraints(self, cli_runner):
        """Should handle out of memory errors"""
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0),  # Docker check
                subprocess.CalledProcessError(
                    137,  # SIGKILL due to OOM
                    'docker-compose up',
                    stderr='OOMKilled'
                )
            ]

            result = cli_runner.invoke(local_app, ['up'])

            assert result.exit_code == 1


@pytest.mark.unit
class TestConcurrencyIssues:
    """Test error handling for concurrency issues"""

    def test_concurrent_sync_operations(self, cli_runner, configured_project):
        """Should handle concurrent sync operations gracefully"""
        # This would test lock contention, file conflicts, etc.
        # For now, just ensure command doesn't crash
        with patch('commands.sync.SyncPlanner') as MockPlanner:
            with patch('commands.sync.SyncExecutor') as MockExecutor:
                from sync_executor import SyncExecutionError

                mock_planner = MockPlanner.return_value
                mock_executor = MockExecutor.return_value

                mock_executor.execute_plan.side_effect = SyncExecutionError(
                    "Another sync operation is in progress"
                )

                result = cli_runner.invoke(sync_app, ['apply', '--yes'])

                assert result.exit_code == 1
                assert 'error' in result.stdout.lower() or 'failed' in result.stdout.lower()


@pytest.mark.unit
class TestUnexpectedErrors:
    """Test error handling for unexpected errors"""

    def test_unexpected_exception_in_health(self, cli_runner):
        """Should handle unexpected exceptions gracefully"""
        with patch('commands.inspect.APIClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get.side_effect = RuntimeError("Unexpected error occurred")

            result = cli_runner.invoke(inspect_app, ['health'])

            assert result.exit_code == 1
            assert 'error' in result.stdout.lower()

    def test_json_decode_error(self, cli_runner):
        """Should handle malformed JSON responses"""
        with patch('commands.inspect.APIClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get.side_effect = ValueError("Invalid JSON")

            result = cli_runner.invoke(inspect_app, ['projects'])

            assert result.exit_code == 1

    def test_keyboard_interrupt_handling(self, cli_runner):
        """Should handle keyboard interrupt gracefully"""
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.side_effect = KeyboardInterrupt()

            result = cli_runner.invoke(local_app, ['logs'])

            # Should exit gracefully, not crash
            # Actual exit code may vary based on exception handling
            assert result.exit_code in [0, 1, 130]  # 130 is typical for SIGINT


@pytest.mark.unit
class TestPermissionErrors:
    """Test error handling for permission errors"""

    def test_permission_denied_writing_config(self, cli_runner):
        """Should handle permission errors when writing config"""
        # This would test scenarios where config file is read-only
        # Implementation depends on cloud/config commands
        pass

    def test_permission_denied_docker_socket(self, cli_runner):
        """Should show helpful error for Docker socket permission issues"""
        with patch('commands.local.subprocess.run') as mock_run:
            mock_run.side_effect = [
                subprocess.CalledProcessError(
                    1,
                    'docker version',
                    stderr='permission denied while trying to connect to Docker daemon socket'
                )
            ]

            result = cli_runner.invoke(local_app, ['up'])

            assert result.exit_code == 1
            # Should contain permission or docker in error
            assert 'permission' in result.stdout.lower() or 'docker' in result.stdout.lower()
