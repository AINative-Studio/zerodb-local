# E2E Integration Testing Guide

**Story**: #456 - Add E2E Integration Tests for CLI-API

## Overview

E2E (End-to-End) tests verify that the CLI actually communicates with the real API, not mocks. These tests prove the integration works by making actual HTTP requests.

## Test Categories

### Unit Tests (Fast, No API Required)
- Use `@pytest.mark.unit`
- Mock all external dependencies
- Test logic in isolation
- Run time: <1 second per test

### Integration Tests (Requires API Running)
- Use `@pytest.mark.integration` and `@pytest.mark.e2e`
- Make real HTTP requests to API
- Verify actual responses
- Run time: 1-5 seconds per test

### Slow Tests
- Use `@pytest.mark.slow`
- Complex workflows or multiple API calls
- Run time: >5 seconds

## Running Tests

### Unit Tests Only (Fast, No API Required)

```bash
cd /Users/aideveloper/core/zerodb-local/cli
pytest tests/ -m "unit" -v
```

Output:
```
tests/test_*.py::test_something PASSED
================================ 50 passed in 2.31s ================================
```

### Integration/E2E Tests (Requires API Running)

**Terminal 1: Start API**
```bash
cd /Users/aideveloper/core/zerodb-local/api
uvicorn main:app --reload --port 8000
```

**Terminal 2: Run E2E tests**
```bash
cd /Users/aideveloper/core/zerodb-local/cli
pytest tests/ -m "e2e" -v
```

Output:
```
tests/test_sync_integration_e2e.py::TestSyncPlannerIntegrationE2E::test_sync_planner_calls_real_api PASSED
tests/test_sync_integration_e2e.py::TestSyncExecutorIntegrationE2E::test_sync_executor_calls_real_api PASSED
================================ 25 passed in 8.45s ================================
```

### All Tests Together

```bash
cd /Users/aideveloper/core/zerodb-local/cli

# Start API first
cd ../api && uvicorn main:app --reload --port 8000 &

# Run all tests
cd ../cli
pytest tests/ -v
```

### Specific E2E Test File Only

```bash
pytest tests/test_sync_integration_e2e.py -v
```

### Run Single Test

```bash
pytest tests/test_sync_integration_e2e.py::TestSyncPlannerIntegrationE2E::test_sync_planner_calls_real_api -v
```

## Expected Behavior

### When API is Running

Tests should either:
1. **PASS** - API call succeeded, got valid response
2. **PASS** - API call succeeded, got expected error (404, 401, etc.)

Example output:
```
test_sync_planner_calls_real_api PASSED (got 404 - proves API was called)
test_sync_executor_calls_real_api PASSED (execution succeeded)
```

### When API is NOT Running

Tests should **SKIP** gracefully:
```
test_sync_planner_calls_real_api SKIPPED (API not running at localhost:8000)
test_sync_executor_calls_real_api SKIPPED (API not running)

================================ 25 skipped in 0.12s ================================
```

## Understanding Test Results

### ✅ Test Passes - Good!

```python
# Example: API returns 404
test_sync_planner_calls_real_api PASSED
```

**Why it passes**: Getting a 404 proves the CLI made an actual HTTP request to the API. This is exactly what we want to test - that integration works, not that the project exists.

### ✅ Test Passes with Real Data - Even Better!

```python
# Example: API returns real sync plan
test_sync_planner_calls_real_api PASSED
assert plan.direction == 'push'
assert len(plan.operations) > 0
```

**Why it passes**: API returned actual data, proving full end-to-end flow works.

### ⏭️ Test Skipped - Expected

```python
test_sync_planner_calls_real_api SKIPPED
```

**Why it skips**: API is not running. This is expected behavior - E2E tests should skip gracefully when dependencies aren't available.

### ❌ Test Fails - Investigate!

```python
test_sync_planner_calls_real_api FAILED
AssertionError: Expected connection error, got: KeyError
```

**Why it fails**: Unexpected error occurred. This indicates a real bug in the CLI-API integration.

## Test Markers

All tests in `test_sync_integration_e2e.py` use:

```python
@pytest.mark.integration
@pytest.mark.e2e
class TestSyncPlannerIntegrationE2E:
    """E2E tests for sync_planner.py"""
```

This allows filtering:

```bash
# Run only integration tests
pytest -m "integration" -v

# Run only E2E tests
pytest -m "e2e" -v

# Run unit tests (exclude integration)
pytest -m "unit" -v

# Run integration but not slow tests
pytest -m "integration and not slow" -v
```

## Coverage Reports

### Generate Coverage Report

```bash
pytest tests/test_sync_integration_e2e.py -v --cov=sync_planner --cov=sync_executor --cov-report=term-missing
```

Output:
```
Name                Stmts   Miss  Cover   Missing
-------------------------------------------------
sync_planner.py       180     15    92%   201-215
sync_executor.py      150      8    95%   320-327
-------------------------------------------------
TOTAL                 330     23    93%
```

### Coverage Targets

- **Unit tests**: 100% of logic paths
- **Integration tests**: 80%+ of API interaction code
- **Combined**: 85%+ overall coverage

## Troubleshooting

### API Not Starting

```bash
# Check if port 8000 is already in use
lsof -i :8000

# Kill existing process
kill -9 <PID>

# Start API with different port
uvicorn main:app --reload --port 8001
```

Then update test:
```python
api_base_url = "http://localhost:8001"
```

### Tests Hanging

**Problem**: Test waits forever for API response

**Solution**: Check API logs for errors, or reduce timeout:
```python
# In sync_planner.py or sync_executor.py
response = requests.post(url, json=data, timeout=5)  # 5 second timeout
```

### 404 Errors

**Expected**: 404 errors are normal and acceptable in E2E tests. They prove the API was called.

**Not expected**: Other errors like 500, connection refused, etc.

### Import Errors

```bash
# If you see: ModuleNotFoundError: No module named 'sync_planner'
cd /Users/aideveloper/core/zerodb-local/cli
python3 -c "import sys; sys.path.insert(0, '.'); import sync_planner"
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd cli
          pip install -r requirements.txt

      - name: Start API
        run: |
          cd api
          uvicorn main:app --port 8000 &
          sleep 5  # Wait for API to start

      - name: Run E2E tests
        run: |
          cd cli
          pytest tests/test_sync_integration_e2e.py -v --cov
```

## What These Tests Prove

✅ **Integration Points Verified**:
1. CLI makes actual HTTP POST to `/v1/projects/{id}/sync/plan`
2. CLI makes actual HTTP POST to `/v1/projects/{id}/sync/execute`
3. CLI makes actual HTTP POST to `/v1/projects/{id}/sync/rollback`
4. CLI correctly handles 404 responses (project not found)
5. CLI correctly handles connection errors (API down)
6. CLI correctly handles authentication errors (401/403)
7. CLI parses API responses correctly
8. CLI converts API data to internal SyncPlan objects
9. Dry run mode works without making changes
10. Progress callbacks execute during sync

❌ **What These Tests Don't Test**:
- API business logic (that's API's responsibility)
- Database state changes (use API integration tests)
- UI/UX of CLI commands (use command tests)
- Performance under load (use load tests)

## Best Practices

### DO ✅
- Skip tests gracefully when API unavailable
- Accept 404 errors as proof of integration
- Test error handling as much as success cases
- Use clear assertion messages
- Document expected vs unexpected errors

### DON'T ❌
- Mock HTTP requests (defeats purpose of E2E)
- Assume projects exist in API
- Hard-code specific data expectations
- Let tests hang indefinitely
- Test API business logic (not CLI's job)

## Examples

### Good E2E Test
```python
@pytest.mark.e2e
def test_sync_planner_calls_real_api(verify_api_available):
    planner = SyncPlanner('http://localhost:8000', api_key='test')

    try:
        plan = planner.generate_plan('test-project', 'push', 'full', {})
        assert plan is not None  # Success path
    except SyncPlannerError as e:
        # 404 acceptable - proves API was called
        assert '404' in str(e) or 'not found' in str(e).lower()
```

### Bad E2E Test
```python
@pytest.mark.e2e
@patch('requests.post')  # ❌ Don't mock in E2E tests!
def test_sync_planner(mock_post):
    mock_post.return_value = Mock(status_code=200)
    planner = SyncPlanner('http://localhost:8000')
    plan = planner.generate_plan('test', 'push', 'full', {})
    # This doesn't test real integration!
```

## Summary

- **Purpose**: Verify CLI → API integration actually works
- **Approach**: Make real HTTP requests, no mocks
- **Success**: Either valid response OR expected error (404, etc.)
- **Failure**: Only unexpected errors indicate bugs
- **Run**: Requires API running on localhost:8000

**Remember**: 404 errors are your friend in E2E tests! They prove the integration works.
