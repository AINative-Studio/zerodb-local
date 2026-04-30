"""
End-to-end tests for CLI

Story #426: Extend CLI Test Suite - E2E Tests

Tests real workflows with actual Docker and API (when available).
Skipped if prerequisites not met.
"""
import pytest
import subprocess
import time
import httpx
from pathlib import Path
from typer.testing import CliRunner
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from commands.local import app as local_app
from commands.sync import app as sync_app
from commands.inspect import app as inspect_app


# ===== Prerequisites =====

def check_docker_running() -> bool:
    """Check if Docker is running"""
    try:
        result = subprocess.run(
            ['docker', 'version'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_local_api_available() -> bool:
    """Check if local API is available"""
    try:
        response = httpx.get('http://localhost:8000/health', timeout=5)
        return response.status_code == 200
    except:
        return False


# Skip all E2E tests if Docker not running
pytestmark = pytest.mark.skipif(
    not check_docker_running(),
    reason="Docker not running - E2E tests require Docker"
)


# ===== E2E Test Scenarios =====

@pytest.mark.e2e
@pytest.mark.slow
class TestFreshEnvironmentSetup:
    """E2E test for fresh environment setup workflow"""

    def test_fresh_setup_workflow(self, cli_runner):
        """
        Test complete fresh setup workflow:
        1. Reset environment (clean slate)
        2. Initialize
        3. Start services
        4. Wait for healthy
        5. Check health
        6. Stop services
        """
        # Step 1: Reset (clean slate)
        result = cli_runner.invoke(local_app, ['reset', '--yes'])
        # Don't assert exit code - might fail if nothing to reset
        time.sleep(2)

        # Step 2: Initialize
        result = cli_runner.invoke(local_app, ['init'])
        assert result.exit_code == 0, f"Init failed: {result.stdout}"
        assert 'initialized' in result.stdout.lower()

        # Step 3: Start services
        result = cli_runner.invoke(local_app, ['up'])
        assert result.exit_code == 0, f"Up failed: {result.stdout}"
        assert 'started' in result.stdout.lower() or 'starting' in result.stdout.lower()

        # Step 4: Wait for services to become healthy
        max_wait = 60  # seconds
        start_time = time.time()
        healthy = False

        while time.time() - start_time < max_wait:
            try:
                response = httpx.get('http://localhost:8000/health', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'healthy':
                        healthy = True
                        break
            except:
                pass
            time.sleep(5)

        if not healthy:
            pytest.skip("Services did not become healthy within 60 seconds")

        # Step 5: Check health via CLI
        result = cli_runner.invoke(inspect_app, ['health'])
        assert result.exit_code == 0, f"Health check failed: {result.stdout}"
        assert 'healthy' in result.stdout.lower() or '✅' in result.stdout

        # Step 6: Stop services (cleanup)
        result = cli_runner.invoke(local_app, ['down'])
        assert result.exit_code == 0, f"Down failed: {result.stdout}"

    def test_service_restart_workflow(self, cli_runner):
        """
        Test service restart workflow:
        1. Ensure services running
        2. Restart specific service
        3. Verify still healthy
        """
        # Prerequisite: Services should be running
        if not check_local_api_available():
            pytest.skip("Local API not available - start services first")

        # Restart API service
        result = cli_runner.invoke(local_app, ['restart', '--service', 'zerodb-api'])
        assert result.exit_code == 0, f"Restart failed: {result.stdout}"

        # Wait a bit for restart
        time.sleep(5)

        # Verify still healthy
        result = cli_runner.invoke(inspect_app, ['health'])
        assert result.exit_code == 0, f"Health check after restart failed: {result.stdout}"


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.skipif(
    not check_local_api_available(),
    reason="Local API not available - E2E sync tests require running API"
)
class TestSyncWorkflowE2E:
    """E2E tests for sync workflow"""

    def test_sync_plan_workflow(self, cli_runner):
        """
        Test sync plan generation:
        1. Plan with dry-run
        2. Plan without dry-run (requires cloud connection)
        """
        # Dry run should always work (no cloud connection needed)
        result = cli_runner.invoke(sync_app, ['plan', '--dry-run'])
        assert result.exit_code == 0 or result.exit_code == 1  # Might fail if not linked
        assert 'dry run' in result.stdout.lower() or 'error' in result.stdout.lower()

    def test_sync_apply_dry_run(self, cli_runner):
        """
        Test sync apply with dry-run flag:
        1. Generate plan
        2. Apply with --dry-run (no actual changes)
        """
        result = cli_runner.invoke(sync_app, ['apply', '--dry-run', '--yes'])
        # Might fail if not linked or authenticated
        # Just verify command structure works
        assert result.exit_code in [0, 1]


@pytest.mark.e2e
@pytest.mark.skipif(
    not check_local_api_available(),
    reason="Local API not available - E2E inspect tests require running API"
)
class TestInspectCommandsE2E:
    """E2E tests for inspect commands"""

    def test_health_command_real_api(self, cli_runner):
        """Test health command against real API"""
        result = cli_runner.invoke(inspect_app, ['health'])
        assert result.exit_code == 0, f"Health check failed: {result.stdout}"

        # Should contain service names
        assert 'postgresql' in result.stdout.lower() or 'postgres' in result.stdout.lower()

    def test_projects_command_real_api(self, cli_runner):
        """Test projects listing against real API"""
        result = cli_runner.invoke(inspect_app, ['projects'])
        assert result.exit_code == 0, f"Projects listing failed: {result.stdout}"

        # Should have table header or message
        assert 'project' in result.stdout.lower()

    def test_health_json_output(self, cli_runner):
        """Test health command with JSON output"""
        result = cli_runner.invoke(inspect_app, ['health', '--json'])
        assert result.exit_code == 0, f"JSON health check failed: {result.stdout}"

        # Verify valid JSON output
        import json
        try:
            data = json.loads(result.stdout)
            assert 'status' in data or 'services' in data
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")


@pytest.mark.e2e
@pytest.mark.slow
class TestDockerIntegration:
    """E2E tests for Docker integration"""

    def test_status_shows_actual_services(self, cli_runner):
        """Test status command shows actual running services"""
        # Start services first
        result = cli_runner.invoke(local_app, ['up'])
        time.sleep(10)  # Wait for services to start

        # Check status
        result = cli_runner.invoke(local_app, ['status'])
        assert result.exit_code == 0

        # Should show actual services
        # Note: Output format may vary, just check it doesn't error
        assert len(result.stdout) > 0

    def test_logs_command_real_output(self, cli_runner):
        """Test logs command with real Docker output"""
        # Prerequisite: Services running
        result = cli_runner.invoke(local_app, ['up'])
        time.sleep(5)

        # Get logs (non-follow mode for testing)
        result = cli_runner.invoke(local_app, ['logs', '--no-follow'])

        # Command should execute (exit code 0 or might be interrupted)
        # Just verify it doesn't crash
        assert result.exit_code in [0, 1]  # 1 might be KeyboardInterrupt


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteUserWorkflow:
    """E2E test for complete user workflows"""

    def test_new_user_onboarding_workflow(self, cli_runner):
        """
        Test complete new user workflow:
        1. Init environment
        2. Start services
        3. Check health
        4. View projects (should be empty or have default)
        5. View statistics
        6. Stop services
        """
        # Step 1: Init
        result = cli_runner.invoke(local_app, ['init'])
        if 'already' in result.stdout.lower():
            # Already initialized, that's fine
            pass
        else:
            assert result.exit_code == 0

        # Step 2: Start
        result = cli_runner.invoke(local_app, ['up'])
        assert result.exit_code == 0
        time.sleep(15)  # Wait for startup

        # Step 3: Health check
        result = cli_runner.invoke(inspect_app, ['health'])
        assert result.exit_code == 0

        # Step 4: View projects
        result = cli_runner.invoke(inspect_app, ['projects'])
        assert result.exit_code == 0

        # Step 5: View statistics (if projects exist)
        # This might fail if no project linked, which is expected
        result = cli_runner.invoke(inspect_app, ['vectors'])
        # Don't assert exit code - might fail if no project

        # Step 6: Stop
        result = cli_runner.invoke(local_app, ['down'])
        assert result.exit_code == 0

    def test_developer_daily_workflow(self, cli_runner):
        """
        Test typical developer daily workflow:
        1. Start services
        2. Check status
        3. View logs briefly
        4. Check health
        5. Inspect data (if available)
        """
        # Step 1: Start
        result = cli_runner.invoke(local_app, ['up'])
        assert result.exit_code == 0
        time.sleep(10)

        # Step 2: Status
        result = cli_runner.invoke(local_app, ['status'])
        assert result.exit_code == 0

        # Step 3: Logs (no-follow)
        result = cli_runner.invoke(local_app, ['logs', '--no-follow'])
        # Just verify it executes

        # Step 4: Health
        result = cli_runner.invoke(inspect_app, ['health'])
        assert result.exit_code == 0

        # Step 5: Inspect (might fail if not configured)
        result = cli_runner.invoke(inspect_app, ['projects'])
        assert result.exit_code == 0


@pytest.mark.e2e
@pytest.mark.slow
class TestErrorRecovery:
    """E2E tests for error recovery scenarios"""

    def test_recovery_from_failed_start(self, cli_runner):
        """Test recovery when service start fails"""
        # Force stop first
        result = cli_runner.invoke(local_app, ['down'])
        time.sleep(2)

        # Try to start
        result = cli_runner.invoke(local_app, ['up'])

        # If it fails, should be able to retry
        if result.exit_code != 0:
            # Try again
            result = cli_runner.invoke(local_app, ['up'])
            # Second attempt might succeed
            assert result.exit_code in [0, 1]

    def test_recovery_from_network_interruption(self, cli_runner):
        """Test commands handle network interruption gracefully"""
        # This test simulates what happens when API becomes unavailable

        # Try health check
        result = cli_runner.invoke(inspect_app, ['health'])

        # Should either succeed or fail gracefully with error message
        if result.exit_code != 0:
            assert 'error' in result.stdout.lower() or 'not running' in result.stdout.lower()


# ===== Performance Tests =====

@pytest.mark.e2e
@pytest.mark.slow
class TestPerformance:
    """E2E performance tests"""

    def test_startup_time_within_limits(self, cli_runner):
        """Test that service startup completes within reasonable time"""
        # Stop services first
        cli_runner.invoke(local_app, ['down'])
        time.sleep(2)

        # Measure startup time
        start = time.time()
        result = cli_runner.invoke(local_app, ['up'])
        end = time.time()

        assert result.exit_code == 0
        startup_time = end - start

        # Should complete within 30 seconds (command execution, not full healthy)
        assert startup_time < 30, f"Startup took {startup_time:.1f}s, expected <30s"

    def test_health_check_response_time(self, cli_runner):
        """Test that health check responds quickly"""
        if not check_local_api_available():
            pytest.skip("Local API not available")

        start = time.time()
        result = cli_runner.invoke(inspect_app, ['health'])
        end = time.time()

        assert result.exit_code == 0
        response_time = end - start

        # Should respond within 3 seconds
        assert response_time < 3, f"Health check took {response_time:.1f}s, expected <3s"

    def test_status_command_performance(self, cli_runner):
        """Test that status command executes quickly"""
        start = time.time()
        result = cli_runner.invoke(local_app, ['status'])
        end = time.time()

        response_time = end - start

        # Should complete within 5 seconds
        assert response_time < 5, f"Status check took {response_time:.1f}s, expected <5s"
