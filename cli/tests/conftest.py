"""
Shared test fixtures and configuration for CLI tests

Story #426: Extend CLI Test Suite
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, MagicMock
from typer.testing import CliRunner
from datetime import datetime, timezone

# Import modules under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from sync_planner import SyncPlan, SyncOperation
from config import CONFIG_DIR, CONFIG_FILE, CREDENTIALS_FILE


# ===== CLI Test Runner =====

@pytest.fixture
def cli_runner():
    """Typer CLI test runner"""
    return CliRunner()


# ===== Temporary Configuration =====

@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory for isolated testing"""
    config_dir = tmp_path / ".zerodb"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Store original paths
    original_config_dir = CONFIG_DIR
    original_config_file = CONFIG_FILE
    original_creds_file = CREDENTIALS_FILE

    # Monkey-patch config module
    import config
    config.CONFIG_DIR = config_dir
    config.CONFIG_FILE = config_dir / "config.json"
    config.CREDENTIALS_FILE = config_dir / "credentials.json"

    yield config_dir

    # Restore original paths
    config.CONFIG_DIR = original_config_dir
    config.CONFIG_FILE = original_config_file
    config.CREDENTIALS_FILE = original_creds_file


@pytest.fixture
def sample_config(temp_config_dir) -> Dict[str, Any]:
    """Sample configuration data"""
    return {
        'active_env': 'local',
        'project_id': 'test-project-123',
        'local_api_url': 'http://localhost:8000',
        'cloud_api_url': 'https://api.ainative.studio'
    }


@pytest.fixture
def sample_credentials(temp_config_dir) -> Dict[str, Any]:
    """Sample cloud credentials"""
    return {
        'access_token': 'test-token-abc123',
        'refresh_token': 'test-refresh-xyz789',
        'username': 'test@example.com',
        'expires_at': '2025-12-31T23:59:59Z'
    }


@pytest.fixture
def configured_project(temp_config_dir, sample_config, sample_credentials):
    """Fixture that sets up config and credentials"""
    import config

    # Write config
    with open(config.CONFIG_FILE, 'w') as f:
        json.dump(sample_config, f)

    # Write credentials
    with open(config.CREDENTIALS_FILE, 'w') as f:
        json.dump(sample_credentials, f)

    return sample_config


# ===== Docker Compose Mocks =====

@pytest.fixture
def mock_docker_compose():
    """Mock docker-compose commands"""
    mock = MagicMock()

    # Default successful responses
    mock.return_value = Mock(
        returncode=0,
        stdout='',
        stderr=''
    )

    # Common docker-compose outputs
    mock.ps_output = '''NAME                    STATUS              HEALTH
zerodb-postgres         running             healthy
zerodb-api             running             healthy
zerodb-dashboard       running             N/A
zerodb-qdrant          running             healthy
zerodb-minio           running             healthy
'''

    mock.version_output = 'Docker version 24.0.0'

    return mock


@pytest.fixture
def docker_not_running(mock_docker_compose):
    """Mock Docker not running scenario"""
    mock_docker_compose.return_value = Mock(returncode=1, stdout='', stderr='Cannot connect to Docker daemon')
    return mock_docker_compose


@pytest.fixture
def docker_not_installed():
    """Mock Docker not installed scenario"""
    def side_effect(*args, **kwargs):
        raise FileNotFoundError("docker: command not found")

    mock = MagicMock()
    mock.side_effect = side_effect
    return mock


# ===== API Client Mocks =====

@pytest.fixture
def mock_api_client():
    """Mock API client with common responses"""
    mock = MagicMock()

    # Health endpoint
    mock.get_health = Mock(return_value={
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'services': {
            'postgresql': {'status': 'healthy', 'response_time_ms': 5},
            'qdrant': {'status': 'healthy', 'response_time_ms': 8},
            'minio': {'status': 'healthy', 'response_time_ms': 3},
            'redpanda': {'status': 'healthy', 'response_time_ms': 4},
            'embeddings': {'status': 'healthy', 'response_time_ms': 10}
        }
    })

    # Projects endpoint
    mock.get_projects = Mock(return_value={
        'projects': [
            {
                'id': 'test-project-123',
                'name': 'Test Project',
                'created_at': '2025-01-01T00:00:00Z',
                'vector_count': 1000,
                'table_count': 5,
                'file_count': 50
            }
        ]
    })

    # Sync state endpoint
    mock.get_sync_state = Mock(return_value={
        'last_sync_at': '2025-12-29T10:00:00Z',
        'direction': 'bidirectional',
        'status': 'completed',
        'pending_changes': 0,
        'conflicts_count': 0,
        'entity_counts': {
            'vectors': {'local': 1000, 'cloud': 1000},
            'tables': {'local': 5, 'cloud': 5},
            'files': {'local': 50, 'cloud': 50}
        }
    })

    # Vector stats endpoint
    mock.get_vector_stats = Mock(return_value={
        'total_vectors': 1000,
        'dimensions': 1536,
        'storage_bytes': 6144000,
        'namespace_count': 3,
        'last_updated': '2025-12-29T12:00:00Z',
        'recent_additions': []
    })

    # Tables endpoint
    mock.get_tables = Mock(return_value={
        'tables': [
            {'name': 'users', 'row_count': 100, 'size_bytes': 10240, 'last_modified': '2025-12-29T11:00:00Z'},
            {'name': 'products', 'row_count': 500, 'size_bytes': 51200, 'last_modified': '2025-12-29T11:30:00Z'}
        ]
    })

    # Files endpoint
    mock.get_files = Mock(return_value={
        'total_files': 50,
        'total_size_bytes': 5242880,
        'file_types': {
            'pdf': {'count': 20, 'size_bytes': 2097152},
            'png': {'count': 30, 'size_bytes': 3145728}
        }
    })

    # Events endpoint
    mock.get_events = Mock(return_value={
        'total_events': 250,
        'event_types': {
            'vector.created': 100,
            'table.updated': 80,
            'file.uploaded': 70
        },
        'oldest_event': '2025-12-20T00:00:00Z',
        'newest_event': '2025-12-29T12:00:00Z',
        'latest_events': []
    })

    return mock


@pytest.fixture
def api_not_reachable():
    """Mock API not reachable scenario"""
    import httpx

    def side_effect(*args, **kwargs):
        raise httpx.ConnectError("Connection refused")

    mock = MagicMock()
    mock.get.side_effect = side_effect
    return mock


@pytest.fixture
def api_timeout():
    """Mock API timeout scenario"""
    import httpx

    def side_effect(*args, **kwargs):
        raise httpx.TimeoutException("Request timeout")

    mock = MagicMock()
    mock.get.side_effect = side_effect
    return mock


# ===== Sample Data =====

@pytest.fixture
def sample_project() -> Dict[str, Any]:
    """Sample project data"""
    return {
        'id': 'test-project-123',
        'name': 'Test Project',
        'description': 'A test project',
        'created_at': '2025-01-01T00:00:00Z',
        'vector_count': 1000,
        'table_count': 5,
        'file_count': 50,
        'memory_count': 200,
        'event_count': 250
    }


@pytest.fixture
def sample_sync_plan() -> SyncPlan:
    """Sample sync plan with operations"""
    plan = SyncPlan(direction='push', mode='incremental')

    # Add vector operations
    plan.operations.append(SyncOperation(
        entity_type='vectors',
        operation='create',
        entity_id='vec-001',
        entity_name='document_embedding_1',
        description='Create vector: document_embedding_1'
    ))

    plan.operations.append(SyncOperation(
        entity_type='vectors',
        operation='update',
        entity_id='vec-002',
        entity_name='document_embedding_2',
        description='Update vector: document_embedding_2'
    ))

    # Add table operations
    plan.operations.append(SyncOperation(
        entity_type='tables',
        operation='upsert',
        entity_id='users',
        entity_name='users',
        description='Upsert table: users (5 rows)'
    ))

    # Add file operations
    plan.operations.append(SyncOperation(
        entity_type='files',
        operation='create',
        entity_id='file-001',
        entity_name='document.pdf',
        description='Upload file: document.pdf'
    ))

    return plan


@pytest.fixture
def sample_sync_plan_with_conflicts() -> SyncPlan:
    """Sample sync plan with conflicts"""
    plan = SyncPlan(direction='bidirectional', mode='incremental')

    # Add operations
    plan.operations.append(SyncOperation(
        entity_type='vectors',
        operation='update',
        entity_id='vec-conflict-1',
        description='Update conflicting vector'
    ))

    # Add conflicts
    plan.conflicts.append({
        'entity_type': 'vectors',
        'entity_id': 'vec-conflict-1',
        'entity_name': 'conflicting_vector',
        'local_version': '2025-12-29T10:00:00Z',
        'cloud_version': '2025-12-29T11:00:00Z',
        'conflict_type': 'modification',
        'description': 'Vector modified in both local and cloud'
    })

    plan.conflicts.append({
        'entity_type': 'tables',
        'entity_id': 'users',
        'entity_name': 'users',
        'local_version': '2025-12-29T09:00:00Z',
        'cloud_version': '2025-12-29T10:00:00Z',
        'conflict_type': 'schema_change',
        'description': 'Table schema differs between local and cloud'
    })

    return plan


# ===== Mock Responses =====

@pytest.fixture
def mock_successful_sync_result():
    """Mock successful sync execution result"""
    return {
        'status': 'success',
        'total_operations': 10,
        'successful': 10,
        'failed': 0,
        'errors': [],
        'duration_seconds': 5.2
    }


@pytest.fixture
def mock_failed_sync_result():
    """Mock failed sync execution result"""
    return {
        'status': 'failed',
        'total_operations': 10,
        'successful': 7,
        'failed': 3,
        'errors': [
            {'operation': 'Create vector: vec-001', 'error': 'Network timeout'},
            {'operation': 'Update table: users', 'error': 'Permission denied'},
            {'operation': 'Upload file: doc.pdf', 'error': 'File too large'}
        ],
        'duration_seconds': 3.8
    }


# ===== Pytest Configuration =====

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (mock external services)"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests (require Docker and API)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests (>5 seconds)"
    )


# ===== Helper Functions =====

@pytest.fixture
def create_temp_docker_compose():
    """Create temporary docker-compose.yml for testing"""
    def _create(content: str = None):
        temp_dir = tempfile.mkdtemp()
        docker_compose_file = Path(temp_dir) / "docker-compose.yml"

        if content is None:
            content = """
version: '3.8'
services:
  postgres:
    image: postgres:14
  api:
    image: zerodb-api:latest
"""

        docker_compose_file.write_text(content)
        return temp_dir, docker_compose_file

    return _create


@pytest.fixture
def cleanup_temp_files():
    """Cleanup temporary test files after tests"""
    temp_files = []

    def _add_file(file_path: Path):
        temp_files.append(file_path)

    yield _add_file

    # Cleanup
    for file_path in temp_files:
        if file_path.exists():
            if file_path.is_dir():
                shutil.rmtree(file_path)
            else:
                file_path.unlink()
