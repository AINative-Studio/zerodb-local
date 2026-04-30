# ZeroDB Local CLI Test Suite

Comprehensive test suite for the ZeroDB Local CLI (Story #426).

## Test Structure

### Test Files

```
tests/
├── conftest.py                      # Shared fixtures and configuration
├── test_local_commands.py          # Local environment command unit tests
├── test_sync_plan.py               # Sync plan generation unit tests
├── test_sync_apply_enhanced.py     # Sync apply execution unit tests
├── test_integration.py             # Integration tests (mocked services)
├── test_e2e.py                     # End-to-end tests (real Docker/API)
├── test_error_handling.py          # Error scenario tests
├── test_command_coverage.py        # Command coverage verification
└── README.md                       # This file
```

### Test Categories (Markers)

- **`@pytest.mark.unit`** - Fast unit tests with mocked dependencies
- **`@pytest.mark.integration`** - Integration tests with mocked external services
- **`@pytest.mark.e2e`** - End-to-end tests requiring Docker and API
- **`@pytest.mark.slow`** - Tests taking >5 seconds

## Running Tests

### All Tests

```bash
cd /Users/aideveloper/core/zerodb-local/cli
pytest
```

### Unit Tests Only (Fast)

```bash
pytest -m unit
```

### Integration Tests

```bash
pytest -m integration
```

### End-to-End Tests (Requires Docker)

```bash
pytest -m e2e
```

### Specific Test File

```bash
pytest tests/test_local_commands.py -v
```

### Specific Test Class

```bash
pytest tests/test_integration.py::TestLocalEnvironmentIntegration -v
```

### Specific Test Function

```bash
pytest tests/test_local_commands.py::TestLocalInit::test_init_creates_directories -v
```

### With Coverage Report

```bash
pytest --cov=. --cov-report=term-missing --cov-report=html
```

Then open the HTML report:

```bash
open htmlcov/index.html
```

### Skip Slow Tests

```bash
pytest -m "not slow"
```

### Verbose Output

```bash
pytest -v -s
```

### Stop on First Failure

```bash
pytest -x
```

### Run Failed Tests Only

```bash
pytest --lf
```

## Coverage Targets

| Metric | Target | Current |
|--------|--------|---------|
| Overall Coverage | ≥80% | Run `pytest --cov` to check |
| Unit Test Coverage | ≥90% | - |
| Integration Test Coverage | ≥80% | - |
| Branch Coverage | ≥75% | - |

## Test Coverage by Module

### Local Commands (`commands/local.py`)

**Total Tests:** ~15 unit + 10 integration

- ✅ `init` - Directory creation, Docker validation
- ✅ `up` - Docker Compose start, health checks
- ✅ `down` - Graceful shutdown, cleanup
- ✅ `status` - Service status display
- ✅ `logs` - Log streaming, filtering
- ✅ `restart` - Service restart, specific services
- ✅ `reset` - Full reset with confirmation

### Sync Commands (`commands/sync.py`)

**Total Tests:** ~20 unit + 15 integration

- ✅ `plan` - Plan generation, dry-run, JSON output
- ✅ `apply` - Execution, conflict resolution, rollback

### Inspect Commands (`commands/inspect.py`)

**Total Tests:** ~10 unit + 8 integration

- ✅ `health` - Health checks, service status
- ✅ `projects` - Project listing
- ✅ `sync` - Sync state display
- ✅ `vectors` - Vector statistics
- ✅ `tables` - Table statistics
- ✅ `files` - File statistics
- ✅ `events` - Event statistics

### Cloud Commands (`commands/cloud.py`)

**Total Tests:** ~8 unit + 5 integration

- ✅ `login` - Authentication, token storage
- ✅ `logout` - Token cleanup
- ✅ `switch` - Environment switching

### Core Modules

**Sync Planner** (`sync_planner.py`)
- ✅ Plan generation for all directions
- ✅ Conflict detection
- ✅ Entity filtering
- ✅ JSON serialization

**Sync Executor** (`sync_executor.py`)
- ✅ Operation execution
- ✅ Error handling
- ✅ Progress reporting
- ✅ Rollback on failure

**Conflict Resolver** (`conflict_resolver.py`)
- ✅ Strategy application (local-wins, cloud-wins, newest-wins, manual)
- ✅ Conflict detection
- ✅ Resolution validation

**API Client** (`api_client.py`)
- ✅ HTTP requests (GET, POST, PUT, DELETE)
- ✅ Error handling
- ✅ Retry logic
- ✅ Response parsing

**Configuration** (`config.py`)
- ✅ Config file management
- ✅ Credential storage
- ✅ Environment switching

## Writing New Tests

### Unit Test Template

```python
@pytest.mark.unit
class TestNewFeature:
    """Test description"""

    def test_specific_behavior(self, cli_runner):
        """Should do something specific"""
        # Arrange
        with patch('module.dependency') as mock_dep:
            mock_dep.return_value = expected_value

            # Act
            result = cli_runner.invoke(app, ['command', '--flag'])

            # Assert
            assert result.exit_code == 0
            assert 'expected text' in result.stdout
```

### Integration Test Template

```python
@pytest.mark.integration
class TestNewWorkflow:
    """Test workflow integration"""

    def test_command_sequence(self, cli_runner, configured_project):
        """Should execute workflow successfully"""
        # Step 1
        result = cli_runner.invoke(app, ['step1'])
        assert result.exit_code == 0

        # Step 2
        result = cli_runner.invoke(app, ['step2'])
        assert result.exit_code == 0
```

### E2E Test Template

```python
@pytest.mark.e2e
@pytest.mark.slow
class TestNewE2EScenario:
    """Test real-world scenario"""

    def test_full_workflow(self, cli_runner):
        """Should complete full workflow with real services"""
        # Real Docker/API interactions
        result = cli_runner.invoke(app, ['command'])
        assert result.exit_code == 0
```

## Fixtures Available

### CLI Fixtures

- `cli_runner` - Typer CLI test runner
- `configured_project` - Project with config and credentials

### Docker Fixtures

- `mock_docker_compose` - Mock Docker Compose commands
- `docker_not_running` - Mock Docker daemon not running
- `docker_not_installed` - Mock Docker not installed

### API Fixtures

- `mock_api_client` - Mock API client with standard responses
- `api_not_reachable` - Mock API connection refused
- `api_timeout` - Mock API timeout

### Data Fixtures

- `sample_config` - Sample configuration
- `sample_credentials` - Sample credentials
- `sample_project` - Sample project data
- `sample_sync_plan` - Sample sync plan
- `sample_sync_plan_with_conflicts` - Sync plan with conflicts

### Temporary Fixtures

- `temp_config_dir` - Temporary config directory
- `create_temp_docker_compose` - Create temp docker-compose.yml
- `cleanup_temp_files` - Auto-cleanup temp files

## Debugging Tests

### Enable Debug Output

```bash
pytest -v -s --log-cli-level=DEBUG
```

### Print Captured Output

```bash
pytest -v -s
```

### Drop into Debugger on Failure

```bash
pytest --pdb
```

### Run with Coverage and HTML Report

```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

## Continuous Integration

Tests run automatically on:
- Every commit (unit + integration)
- Pull requests (unit + integration + e2e if Docker available)
- Pre-merge (full suite including e2e)

## Known Test Limitations

### E2E Tests

- Require Docker daemon running
- Require 60+ seconds for service startup
- May fail intermittently due to network/timing
- Skipped automatically if Docker not available

### Mock Limitations

- Docker Compose output format may change
- API response schemas assumed stable
- Some edge cases may not be covered

## Test Maintenance

### When Adding New Commands

1. Add unit tests in `test_{module}_commands.py`
2. Add integration tests in `test_integration.py`
3. Add command coverage in `test_command_coverage.py`
4. Update this README

### When Changing API Schemas

1. Update fixtures in `conftest.py`
2. Update mock responses in relevant test files
3. Run full test suite to verify

### When Adding New Error Scenarios

1. Add tests to `test_error_handling.py`
2. Verify error messages are clear and actionable
3. Test graceful degradation

## Getting Help

- **CI Failures**: Check GitHub Actions logs for details
- **Coverage Issues**: Run `pytest --cov-report=html` and review missing lines
- **Fixture Issues**: Check `conftest.py` for available fixtures
- **Mock Issues**: Verify mock setup in test file or conftest

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Typer Testing](https://typer.tiangolo.com/tutorial/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [ZeroDB CLI Repository](https://github.com/ainative/zerodb-local)
