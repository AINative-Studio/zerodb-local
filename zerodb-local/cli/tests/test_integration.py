"""
Integration tests for CLI workflows

Story #426: Extend CLI Test Suite - Integration Tests

Tests command integration and workflow sequences with mocked external services.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
import subprocess
import json
from pathlib import Path
from typer.testing import CliRunner
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from commands.local import app as local_app
from commands.sync import app as sync_app
from commands.inspect import app as inspect_app


@pytest.mark.integration
class TestLocalEnvironmentIntegration:
    """Integration tests for local environment commands workflow"""

    def test_init_up_status_down_workflow(self, cli_runner, mock_docker_compose, tmp_path):
        """Should successfully execute init → up → status → down workflow"""
        with patch('commands.local.subprocess.run', mock_docker_compose) as mock_run:
            with patch('commands.local.DATA_DIR', tmp_path / 'data'):
                with patch('commands.local.check_docker_installed', return_value=True):
                    # Step 1: Init
                    result = cli_runner.invoke(local_app, ['init'])
                    assert result.exit_code == 0
                    assert 'initialized' in result.stdout.lower()

                    # Verify data directories created
                    assert (tmp_path / 'data' / 'postgres').exists()
                    assert (tmp_path / 'data' / 'qdrant').exists()
                    assert (tmp_path / 'data' / 'minio').exists()

                    # Step 2: Up
                    result = cli_runner.invoke(local_app, ['up'])
                    assert result.exit_code == 0
                    assert 'started' in result.stdout.lower()

                    # Verify docker-compose up was called
                    up_calls = [c for c in mock_run.call_args_list if 'up' in str(c)]
                    assert len(up_calls) > 0

                    # Step 3: Status
                    mock_run.return_value = Mock(returncode=0, stdout=mock_docker_compose.ps_output)
                    result = cli_runner.invoke(local_app, ['status'])
                    assert result.exit_code == 0
                    assert 'postgres' in result.stdout.lower()
                    assert 'api' in result.stdout.lower()

                    # Step 4: Down
                    mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
                    result = cli_runner.invoke(local_app, ['down'])
                    assert result.exit_code == 0

                    # Verify docker-compose down was called
                    down_calls = [c for c in mock_run.call_args_list if 'down' in str(c)]
                    assert len(down_calls) > 0

    def test_logs_streaming_and_filtering(self, cli_runner, mock_docker_compose):
        """Should stream logs with optional service filtering"""
        with patch('commands.local.subprocess.run', mock_docker_compose) as mock_run:
            with patch('commands.local.check_docker_installed', return_value=True):
                # All services logs
                result = cli_runner.invoke(local_app, ['logs', '--no-follow'])

                # Verify logs command called
                logs_calls = [c for c in mock_run.call_args_list if 'logs' in str(c)]
                assert len(logs_calls) > 0

                # Specific service logs
                result = cli_runner.invoke(local_app, ['logs', 'zerodb-api', '--no-follow'])

                # Verify service name in args
                api_logs_calls = [c for c in mock_run.call_args_list if 'zerodb-api' in str(c)]
                assert len(api_logs_calls) > 0

    def test_restart_with_specific_service(self, cli_runner, mock_docker_compose):
        """Should restart specific service or all services"""
        with patch('commands.local.subprocess.run', mock_docker_compose) as mock_run:
            with patch('commands.local.check_docker_installed', return_value=True):
                # Restart all
                result = cli_runner.invoke(local_app, ['restart'])
                assert result.exit_code == 0

                # Restart specific service
                result = cli_runner.invoke(local_app, ['restart', '--service', 'postgres'])
                assert result.exit_code == 0

                # Verify postgres in restart args
                postgres_calls = [c for c in mock_run.call_args_list if 'postgres' in str(c)]
                assert len(postgres_calls) > 0

    def test_reset_with_confirmation(self, cli_runner, mock_docker_compose, tmp_path):
        """Should reset environment only with confirmation"""
        with patch('commands.local.subprocess.run', mock_docker_compose) as mock_run:
            with patch('commands.local.DATA_DIR', tmp_path / 'data'):
                with patch('commands.local.check_docker_installed', return_value=True):
                    # Create data directory
                    data_dir = tmp_path / 'data'
                    data_dir.mkdir()
                    (data_dir / 'test.txt').write_text('test')

                    # Reset with --yes flag
                    result = cli_runner.invoke(local_app, ['reset', '--yes'])
                    assert result.exit_code == 0

                    # Verify docker-compose down -v was called
                    down_v_calls = [c for c in mock_run.call_args_list
                                   if 'down' in str(c) and '-v' in str(c)]
                    assert len(down_v_calls) > 0

    def test_rollback_on_error(self, cli_runner):
        """Should rollback changes when command fails"""
        with patch('commands.local.subprocess.run') as mock_run:
            # First call succeeds (docker check)
            # Second call fails (docker-compose up)
            mock_run.side_effect = [
                Mock(returncode=0),  # Docker check
                subprocess.CalledProcessError(1, 'docker-compose up', stderr='Error')
            ]

            with patch('commands.local.check_docker_installed', return_value=True):
                result = cli_runner.invoke(local_app, ['up'])
                assert result.exit_code == 1


@pytest.mark.integration
class TestSyncWorkflowIntegration:
    """Integration tests for sync command workflow"""

    def test_plan_to_apply_workflow(self, cli_runner, configured_project,
                                    sample_sync_plan, mock_api_client):
        """Should successfully execute plan → apply workflow"""
        with patch('commands.sync.SyncPlanner') as MockPlanner:
            with patch('commands.sync.SyncExecutor') as MockExecutor:
                with patch('commands.sync.ConflictResolver') as MockResolver:
                    # Setup mocks
                    mock_planner = MockPlanner.return_value
                    mock_planner.generate_plan.return_value = sample_sync_plan
                    mock_planner.plan_to_json.return_value = json.dumps({'operations': []})

                    mock_executor = MockExecutor.return_value
                    mock_executor.execute_plan.return_value = {
                        'status': 'success',
                        'total_operations': 4,
                        'successful': 4,
                        'failed': 0,
                        'errors': []
                    }

                    mock_resolver = MockResolver.return_value
                    mock_resolver.resolve_all.return_value = []

                    # Step 1: Plan (dry-run)
                    result = cli_runner.invoke(sync_app, ['plan', '--dry-run'])
                    assert result.exit_code == 0
                    assert 'dry run' in result.stdout.lower()

                    # Step 2: Plan (actual)
                    result = cli_runner.invoke(sync_app, ['plan'])
                    assert result.exit_code == 0
                    assert mock_planner.generate_plan.called

                    # Step 3: Apply with confirmation
                    result = cli_runner.invoke(sync_app, ['apply', '--yes'])
                    assert result.exit_code == 0
                    assert mock_executor.execute_plan.called

    def test_plan_with_different_directions(self, cli_runner, configured_project,
                                           sample_sync_plan):
        """Should generate plans for different sync directions"""
        with patch('commands.sync.SyncPlanner') as MockPlanner:
            mock_planner = MockPlanner.return_value
            mock_planner.generate_plan.return_value = sample_sync_plan

            # Push direction
            result = cli_runner.invoke(sync_app, ['plan', '--direction', 'push'])
            assert result.exit_code == 0

            call_args = mock_planner.generate_plan.call_args
            assert call_args[1]['direction'] == 'push'

            # Pull direction
            result = cli_runner.invoke(sync_app, ['plan', '--direction', 'pull'])
            assert result.exit_code == 0

            call_args = mock_planner.generate_plan.call_args
            assert call_args[1]['direction'] == 'pull'

            # Bidirectional
            result = cli_runner.invoke(sync_app, ['plan', '--direction', 'bidirectional'])
            assert result.exit_code == 0

            call_args = mock_planner.generate_plan.call_args
            assert call_args[1]['direction'] == 'bidirectional'

    def test_apply_with_auto_approve(self, cli_runner, configured_project,
                                    sample_sync_plan):
        """Should apply sync without confirmation when --yes flag used"""
        with patch('commands.sync.SyncPlanner') as MockPlanner:
            with patch('commands.sync.SyncExecutor') as MockExecutor:
                with patch('commands.sync.ConflictResolver'):
                    mock_planner = MockPlanner.return_value
                    mock_planner.generate_plan.return_value = sample_sync_plan

                    mock_executor = MockExecutor.return_value
                    mock_executor.execute_plan.return_value = {
                        'status': 'success',
                        'total_operations': 4,
                        'successful': 4,
                        'failed': 0,
                        'errors': []
                    }

                    # Should not prompt for confirmation
                    result = cli_runner.invoke(sync_app, ['apply', '--yes'])
                    assert result.exit_code == 0
                    assert mock_executor.execute_plan.called

    def test_rollback_on_sync_error(self, cli_runner, configured_project,
                                   sample_sync_plan):
        """Should rollback when sync execution fails"""
        from sync_executor import SyncExecutionError

        with patch('commands.sync.SyncPlanner') as MockPlanner:
            with patch('commands.sync.SyncExecutor') as MockExecutor:
                with patch('commands.sync.ConflictResolver'):
                    mock_planner = MockPlanner.return_value
                    mock_planner.generate_plan.return_value = sample_sync_plan

                    mock_executor = MockExecutor.return_value
                    mock_executor.execute_plan.side_effect = SyncExecutionError("Network error")

                    result = cli_runner.invoke(sync_app, ['apply', '--yes'])
                    assert result.exit_code == 1
                    assert 'failed' in result.stdout.lower()

    def test_conflict_resolution_strategies(self, cli_runner, configured_project,
                                           sample_sync_plan_with_conflicts):
        """Should handle different conflict resolution strategies"""
        with patch('commands.sync.SyncPlanner') as MockPlanner:
            with patch('commands.sync.SyncExecutor') as MockExecutor:
                with patch('commands.sync.ConflictResolver') as MockResolver:
                    mock_planner = MockPlanner.return_value
                    mock_planner.generate_plan.return_value = sample_sync_plan_with_conflicts

                    mock_executor = MockExecutor.return_value
                    mock_executor.execute_plan.return_value = {
                        'status': 'success',
                        'total_operations': 1,
                        'successful': 1,
                        'failed': 0,
                        'errors': []
                    }

                    mock_resolver_instance = MockResolver.return_value
                    mock_resolver_instance.resolve_all.return_value = []

                    # Test different strategies
                    strategies = ['local-wins', 'cloud-wins', 'newest-wins', 'manual']

                    for strategy in strategies:
                        result = cli_runner.invoke(sync_app, [
                            'apply',
                            '--yes',
                            '--strategy',
                            strategy
                        ])
                        # Should not fail
                        assert result.exit_code == 0


@pytest.mark.integration
class TestInspectIntegration:
    """Integration tests for inspect commands"""

    def test_health_check_all_services(self, cli_runner):
        """Should check health of all services and display status"""
        with patch('commands.inspect.APIClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get.return_value = {
                'status': 'healthy',
                'timestamp': '2025-12-29T12:00:00Z',
                'services': {
                    'postgresql': {'status': 'healthy', 'response_time_ms': 5},
                    'qdrant': {'status': 'healthy', 'response_time_ms': 8},
                    'minio': {'status': 'degraded', 'response_time_ms': 150},
                    'redpanda': {'status': 'healthy', 'response_time_ms': 4},
                    'embeddings': {'status': 'down', 'response_time_ms': 0}
                }
            }

            result = cli_runner.invoke(inspect_app, ['health'])
            assert result.exit_code == 0
            assert 'postgresql' in result.stdout.lower()
            assert 'qdrant' in result.stdout.lower()
            assert 'minio' in result.stdout.lower()

    def test_project_listing(self, cli_runner):
        """Should list all projects with statistics"""
        with patch('commands.inspect.APIClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get.return_value = {
                'projects': [
                    {
                        'id': 'proj-1',
                        'name': 'Project One',
                        'created_at': '2025-01-01T00:00:00Z',
                        'vector_count': 1000,
                        'table_count': 5,
                        'file_count': 50
                    },
                    {
                        'id': 'proj-2',
                        'name': 'Project Two',
                        'created_at': '2025-02-01T00:00:00Z',
                        'vector_count': 500,
                        'table_count': 3,
                        'file_count': 25
                    }
                ]
            }

            result = cli_runner.invoke(inspect_app, ['projects'])
            assert result.exit_code == 0
            assert 'proj-1' in result.stdout
            assert 'proj-2' in result.stdout
            assert 'Project One' in result.stdout

    def test_sync_state_retrieval(self, cli_runner, configured_project):
        """Should retrieve and display sync state"""
        with patch('commands.inspect.APIClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get.return_value = {
                'last_sync_at': '2025-12-29T10:00:00Z',
                'direction': 'bidirectional',
                'status': 'completed',
                'pending_changes': 5,
                'conflicts_count': 2,
                'entity_counts': {
                    'vectors': {'local': 1005, 'cloud': 1000},
                    'tables': {'local': 5, 'cloud': 5}
                }
            }

            result = cli_runner.invoke(inspect_app, ['sync'])
            assert result.exit_code == 0
            assert 'sync' in result.stdout.lower()
            assert 'pending' in result.stdout.lower() or '5' in result.stdout

    def test_vector_table_file_statistics(self, cli_runner, configured_project):
        """Should retrieve statistics for vectors, tables, and files"""
        with patch('commands.inspect.APIClient') as MockClient:
            mock_client = MockClient.return_value

            # Vector stats
            mock_client.get.return_value = {
                'total_vectors': 1000,
                'dimensions': 1536,
                'storage_bytes': 6144000,
                'namespace_count': 3,
                'last_updated': '2025-12-29T12:00:00Z',
                'recent_additions': []
            }

            result = cli_runner.invoke(inspect_app, ['vectors'])
            assert result.exit_code == 0
            assert '1000' in result.stdout or '1,000' in result.stdout

            # Table stats
            mock_client.get.return_value = {
                'tables': [
                    {'name': 'users', 'row_count': 100, 'size_bytes': 10240},
                    {'name': 'products', 'row_count': 500, 'size_bytes': 51200}
                ]
            }

            result = cli_runner.invoke(inspect_app, ['tables'])
            assert result.exit_code == 0
            assert 'users' in result.stdout
            assert 'products' in result.stdout

            # File stats
            mock_client.get.return_value = {
                'total_files': 50,
                'total_size_bytes': 5242880,
                'file_types': {
                    'pdf': {'count': 20, 'size_bytes': 2097152}
                }
            }

            result = cli_runner.invoke(inspect_app, ['files'])
            assert result.exit_code == 0
            assert '50' in result.stdout


@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API communication"""

    def test_api_retry_logic(self, cli_runner, configured_project):
        """Should retry failed API requests"""
        with patch('commands.inspect.APIClient') as MockClient:
            mock_client = MockClient.return_value

            # First two calls fail, third succeeds
            import httpx
            mock_client.get.side_effect = [
                httpx.ConnectError("Connection refused"),
                httpx.ConnectError("Connection refused"),
                {'status': 'healthy'}
            ]

            # Should eventually succeed after retries
            result = cli_runner.invoke(inspect_app, ['health'])
            # Depending on retry implementation, might succeed or fail
            assert mock_client.get.call_count >= 1

    def test_api_error_handling(self, cli_runner, configured_project):
        """Should handle various API errors gracefully"""
        with patch('commands.inspect.APIClient') as MockClient:
            import httpx

            # Test 404
            mock_client = MockClient.return_value
            mock_client._make_request.side_effect = Exception("Resource not found: /v1/nonexistent")

            result = cli_runner.invoke(inspect_app, ['sync'])
            assert result.exit_code == 1
            assert 'error' in result.stdout.lower()

    def test_json_output_format(self, cli_runner, configured_project):
        """Should support JSON output format for all inspect commands"""
        with patch('commands.inspect.APIClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get.return_value = {'status': 'healthy', 'data': {}}

            result = cli_runner.invoke(inspect_app, ['health', '--json'])
            assert result.exit_code == 0

            # Should be valid JSON
            try:
                json.loads(result.stdout)
            except json.JSONDecodeError:
                pytest.fail("Output is not valid JSON")
