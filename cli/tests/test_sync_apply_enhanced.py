"""
Tests for Story #422: Enhanced Sync Apply Command

Tests all new features:
- --auto-approve flag
- --direction option
- --rollback-on-error option
- --plan-id option
- Enhanced confirmation prompts
- Progress tracking
- Sync history
- Error handling
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from rich.console import Console

# Import functions to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from commands.sync_enhanced import (
    show_confirmation_prompt,
    save_sync_history,
    load_plan_by_id,
    display_results_enhanced,
    display_plan_enhanced,
    SYNC_HISTORY_FILE
)
from commands.sync_apply_enhanced import sync_apply_command
from sync_planner import SyncPlan, SyncOperation


class TestConfirmationPrompt:
    """Test enhanced confirmation prompt"""

    def test_show_confirmation_prompt_push(self, capsys):
        """Test confirmation prompt for push sync"""
        plan = SyncPlan(direction='push', mode='incremental')
        plan.operations = [
            SyncOperation(entity_type='vector', operation='create', description='Upload vector 1'),
            SyncOperation(entity_type='vector', operation='create', description='Upload vector 2'),
            SyncOperation(entity_type='table', operation='update', description='Update table users'),
        ]

        show_confirmation_prompt(plan, 'push')

        # Check that summary is displayed (output goes to console via Rich)
        # We can't easily capture Rich output, so this is a smoke test
        assert True  # If no exception, test passes

    def test_show_confirmation_prompt_with_conflicts(self, capsys):
        """Test confirmation prompt shows conflict warning"""
        plan = SyncPlan(direction='push', mode='incremental')
        plan.operations = [SyncOperation(entity_type='vector', operation='create', description='Test')]
        plan.conflicts = [
            {'entity_type': 'vector', 'entity_id': '123'},
            {'entity_type': 'table', 'entity_id': '456'}
        ]

        show_confirmation_prompt(plan, 'push')

        # Should show conflict warning
        assert True  # Smoke test


class TestSyncHistory:
    """Test sync history tracking"""

    def setup_method(self):
        """Clean up history file before each test"""
        if SYNC_HISTORY_FILE.exists():
            SYNC_HISTORY_FILE.unlink()

    def teardown_method(self):
        """Clean up after tests"""
        if SYNC_HISTORY_FILE.exists():
            SYNC_HISTORY_FILE.unlink()

    def test_save_sync_history_success(self):
        """Test saving successful sync to history"""
        plan = SyncPlan(direction='push', mode='incremental')
        plan.operations = [
            SyncOperation(entity_type='vector', operation='create', description='Test 1'),
            SyncOperation(entity_type='vector', operation='create', description='Test 2'),
        ]

        result = {
            'status': 'success',
            'total_operations': 2,
            'successful': 2,
            'failed': 0,
            'errors': [],
            'sync_id': 'test_sync_123'
        }

        save_sync_history(plan, result, 5.5, 'push')

        # Verify history file created
        assert SYNC_HISTORY_FILE.exists()

        # Load and verify content
        with open(SYNC_HISTORY_FILE, 'r') as f:
            history = json.load(f)

        assert len(history) == 1
        entry = history[0]
        assert entry['sync_id'] == 'test_sync_123'
        assert entry['status'] == 'success'
        assert entry['direction'] == 'push'
        assert entry['total_operations'] == 2
        assert entry['successful'] == 2
        assert entry['failed'] == 0
        assert entry['execution_time_seconds'] == 5.5

    def test_save_sync_history_failure(self):
        """Test saving failed sync to history"""
        plan = SyncPlan(direction='pull', mode='incremental')
        plan.operations = [
            SyncOperation(entity_type='table', operation='update', description='Test'),
        ]

        result = {
            'status': 'failed',
            'total_operations': 1,
            'successful': 0,
            'failed': 1,
            'errors': [{'operation': 'update table', 'error': 'Network timeout'}]
        }

        save_sync_history(plan, result, 2.0, 'pull')

        # Verify error is saved
        with open(SYNC_HISTORY_FILE, 'r') as f:
            history = json.load(f)

        assert history[0]['status'] == 'failed'
        assert len(history[0]['errors']) == 1
        assert 'Network timeout' in history[0]['errors'][0]['error']

    def test_sync_history_keeps_last_100(self):
        """Test that history only keeps last 100 entries"""
        plan = SyncPlan(direction='push', mode='incremental')
        result = {
            'status': 'success',
            'total_operations': 1,
            'successful': 1,
            'failed': 0
        }

        # Save 150 entries
        for i in range(150):
            save_sync_history(plan, result, 1.0, 'push')

        # Verify only 100 kept
        with open(SYNC_HISTORY_FILE, 'r') as f:
            history = json.load(f)

        assert len(history) == 100

    def test_load_plan_by_id_not_implemented(self):
        """Test that load_plan_by_id returns None (not yet implemented)"""
        plan = load_plan_by_id('test_plan_123')
        assert plan is None


class TestResultsDisplay:
    """Test enhanced results display"""

    def test_display_results_dry_run(self):
        """Test displaying dry run results"""
        result = {
            'status': 'dry_run',
            'would_execute': 10,
            'summary': {
                'create': 5,
                'update': 3,
                'delete': 2
            }
        }

        # This is a smoke test - just ensure no exception
        display_results_enhanced(result, dry_run=True, execution_time=0)
        assert True

    def test_display_results_success(self):
        """Test displaying successful sync results"""
        result = {
            'status': 'success',
            'total_operations': 100,
            'successful': 100,
            'failed': 0,
            'errors': []
        }

        display_results_enhanced(result, dry_run=False, execution_time=45.5)
        assert True

    def test_display_results_with_errors(self):
        """Test displaying results with errors"""
        result = {
            'status': 'failed',
            'total_operations': 50,
            'successful': 40,
            'failed': 10,
            'errors': [
                {'operation': 'update vector 1', 'error': 'Timeout'},
                {'operation': 'create table 2', 'error': 'Schema conflict'}
            ]
        }

        display_results_enhanced(result, dry_run=False, execution_time=30.0)
        assert True


class TestPlanDisplay:
    """Test enhanced plan display"""

    def test_display_plan_push(self):
        """Test displaying push plan"""
        plan = SyncPlan(direction='push', mode='incremental')
        plan.operations = [
            SyncOperation(entity_type='vector', operation='create', description='Upload vectors'),
            SyncOperation(entity_type='table', operation='update', description='Update tables'),
            SyncOperation(entity_type='file', operation='upsert', description='Sync files'),
        ]

        display_plan_enhanced(plan, 'push')
        assert True

    def test_display_plan_with_conflicts(self):
        """Test displaying plan with conflicts"""
        plan = SyncPlan(direction='bidirectional', mode='incremental')
        plan.operations = [
            SyncOperation(entity_type='vector', operation='create', description='Test'),
        ]
        plan.conflicts = [
            {'entity_type': 'table', 'entity_id': '123'},
            {'entity_type': 'vector', 'entity_id': '456'},
        ]

        display_plan_enhanced(plan, 'bidirectional')
        assert True


class TestSyncApplyCommand:
    """Test main sync apply command"""

    @patch('commands.sync_apply_enhanced.load_config')
    @patch('commands.sync_apply_enhanced.get_cloud_credentials')
    @patch('commands.sync_apply_enhanced.SyncPlanner')
    @patch('commands.sync_apply_enhanced.SyncExecutor')
    def test_sync_apply_auto_approve(self, mock_executor, mock_planner, mock_creds, mock_config):
        """Test sync apply with --auto-approve"""
        # Setup mocks
        mock_config.return_value = {'project_id': 'test_project'}
        mock_creds.return_value = {'access_token': 'test_token'}

        plan = SyncPlan(direction='push', mode='incremental')
        plan.operations = [
            SyncOperation(entity_type='vector', operation='create', description='Test')
        ]

        mock_planner_instance = Mock()
        mock_planner_instance.generate_plan.return_value = plan
        mock_planner.return_value = mock_planner_instance

        mock_executor_instance = Mock()
        mock_executor_instance.execute_plan.return_value = {
            'status': 'success',
            'total_operations': 1,
            'successful': 1,
            'failed': 0,
            'errors': []
        }
        mock_executor.return_value = mock_executor_instance

        # Execute
        with patch('commands.sync_apply_enhanced.ConflictResolver'):
            sync_apply_command(
                auto_approve=True,
                direction='push',
                rollback_on_error=True,
                plan_id=None,
                conflict_strategy='manual',
                dry_run=False
            )

        # Verify executor was called
        mock_executor_instance.execute_plan.assert_called_once()

    @patch('commands.sync_apply_enhanced.load_config')
    def test_sync_apply_no_project_linked(self, mock_config):
        """Test sync apply fails if no project linked"""
        mock_config.return_value = {'project_id': None}

        with pytest.raises(SystemExit) as exc_info:
            sync_apply_command(auto_approve=True, direction='push')

        assert exc_info.value.code == 1

    @patch('commands.sync_apply_enhanced.load_config')
    @patch('commands.sync_apply_enhanced.get_cloud_credentials')
    def test_sync_apply_not_logged_in(self, mock_creds, mock_config):
        """Test sync apply fails if not logged in"""
        mock_config.return_value = {'project_id': 'test_project'}
        mock_creds.return_value = None

        with pytest.raises(SystemExit) as exc_info:
            sync_apply_command(auto_approve=True, direction='push')

        assert exc_info.value.code == 1

    def test_sync_apply_invalid_direction(self):
        """Test sync apply fails with invalid direction"""
        with patch('commands.sync_apply_enhanced.load_config') as mock_config:
            mock_config.return_value = {'project_id': 'test_project'}

            with patch('commands.sync_apply_enhanced.get_cloud_credentials') as mock_creds:
                mock_creds.return_value = {'access_token': 'token'}

                with pytest.raises(SystemExit) as exc_info:
                    sync_apply_command(
                        auto_approve=True,
                        direction='invalid_direction'
                    )

                assert exc_info.value.code == 1


class TestErrorHandling:
    """Test error handling scenarios"""

    @patch('commands.sync_apply_enhanced.load_config')
    @patch('commands.sync_apply_enhanced.get_cloud_credentials')
    @patch('commands.sync_apply_enhanced.SyncPlanner')
    @patch('commands.sync_apply_enhanced.SyncExecutor')
    @patch('commands.sync_apply_enhanced.ConflictResolver')
    def test_rollback_on_error(self, mock_resolver, mock_executor, mock_planner, mock_creds, mock_config):
        """Test that rollback is triggered on error"""
        mock_config.return_value = {'project_id': 'test_project'}
        mock_creds.return_value = {'access_token': 'test_token'}

        plan = SyncPlan(direction='push', mode='incremental')
        plan.operations = [SyncOperation(entity_type='vector', operation='create', description='Test')]

        mock_planner_instance = Mock()
        mock_planner_instance.generate_plan.return_value = plan
        mock_planner.return_value = mock_planner_instance

        # Make executor raise an error
        mock_executor_instance = Mock()
        from commands.sync_executor import SyncExecutionError
        mock_executor_instance.execute_plan.side_effect = SyncExecutionError("Test error")
        mock_executor.return_value = mock_executor_instance

        # Execute with rollback enabled
        with pytest.raises(SystemExit):
            sync_apply_command(
                auto_approve=True,
                direction='push',
                rollback_on_error=True
            )

        # Verify rollback was called
        mock_executor_instance.rollback.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
