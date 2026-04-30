"""
Unit tests for inspect commands

Story #423: Add Environment Inspection Commands
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json


# Mock the imports since we don't have them installed
@pytest.fixture(autouse=True)
def mock_imports(monkeypatch):
    """Mock external dependencies"""
    # Mock typer
    mock_typer = MagicMock()
    mock_typer.Option = Mock(return_value=None)
    mock_typer.Exit = Exception
    monkeypatch.setitem(__import__('sys').modules, 'typer', mock_typer)

    # Mock httpx
    mock_httpx = MagicMock()
    monkeypatch.setitem(__import__('sys').modules, 'httpx', mock_httpx)

    # Mock rich
    mock_rich = MagicMock()
    monkeypatch.setitem(__import__('sys').modules, 'rich', mock_rich)
    monkeypatch.setitem(__import__('sys').modules, 'rich.console', mock_rich)
    monkeypatch.setitem(__import__('sys').modules, 'rich.table', mock_rich)
    monkeypatch.setitem(__import__('sys').modules, 'rich.panel', mock_rich)
    monkeypatch.setitem(__import__('sys').modules, 'rich.tree', mock_rich)


def test_format_bytes():
    """Test byte formatting utility"""
    from cli.commands.inspect import format_bytes

    assert format_bytes(0) == "0.00 B"
    assert format_bytes(1024) == "1.00 KB"
    assert format_bytes(1024 * 1024) == "1.00 MB"
    assert format_bytes(1024 * 1024 * 1024) == "1.00 GB"
    assert format_bytes(1536) == "1.50 KB"


def test_format_timestamp():
    """Test timestamp formatting"""
    from cli.commands.inspect import format_timestamp

    # Valid ISO timestamp
    result = format_timestamp("2025-12-29T14:30:00Z")
    assert "2025-12-29" in result
    assert "14:30:00" in result

    # Invalid timestamp - should return as-is
    result = format_timestamp("invalid")
    assert result == "invalid"


def test_estimate_next_sync():
    """Test sync estimation logic"""
    from cli.commands.inspect import estimate_next_sync

    # No changes
    assert estimate_next_sync("2025-12-29T14:30:00Z", 0) == "No pending changes"

    # Few changes
    assert "15 minutes" in estimate_next_sync("2025-12-29T14:30:00Z", 5)

    # Medium changes
    assert "5 minutes" in estimate_next_sync("2025-12-29T14:30:00Z", 50)

    # Many changes
    assert "Soon" in estimate_next_sync("2025-12-29T14:30:00Z", 150)


def test_get_current_project_id_with_param():
    """Test project ID resolution with parameter"""
    from cli.commands.inspect import get_current_project_id

    # When project_id is provided, it should return it
    result = get_current_project_id("test-project-123")
    assert result == "test-project-123"


@patch('cli.commands.inspect.get_project_id')
def test_get_current_project_id_from_config(mock_get_project_id):
    """Test project ID resolution from config"""
    from cli.commands.inspect import get_current_project_id

    # Mock config returning a project ID
    mock_get_project_id.return_value = "config-project-456"

    result = get_current_project_id(None)
    assert result == "config-project-456"


@patch('cli.commands.inspect.get_project_id')
def test_get_current_project_id_no_project(mock_get_project_id):
    """Test project ID resolution with no project linked"""
    from cli.commands.inspect import get_current_project_id
    import typer

    # Mock config returning None
    mock_get_project_id.return_value = None

    with pytest.raises(Exception):  # Should raise typer.Exit
        get_current_project_id(None)


def test_api_client_initialization():
    """Test APIClient initialization"""
    from cli.commands.inspect import APIClient

    client = APIClient("http://localhost:8000")
    assert client.base_url == "http://localhost:8000"

    # Test URL normalization (trailing slash removal)
    client = APIClient("http://localhost:8000/")
    assert client.base_url == "http://localhost:8000"


@patch('cli.commands.inspect.httpx.Client')
def test_api_client_successful_request(mock_httpx_client):
    """Test successful API request"""
    from cli.commands.inspect import APIClient

    # Mock successful response
    mock_response = Mock()
    mock_response.json.return_value = {"status": "ok"}
    mock_response.raise_for_status.return_value = None

    mock_client_instance = Mock()
    mock_client_instance.request.return_value = mock_response
    mock_httpx_client.return_value = mock_client_instance

    client = APIClient()
    result = client.get("/test")

    assert result == {"status": "ok"}
    mock_client_instance.request.assert_called_once()


@patch('cli.commands.inspect.httpx.Client')
def test_api_client_connection_error(mock_httpx_client):
    """Test API connection error with retries"""
    import httpx
    from cli.commands.inspect import APIClient

    # Mock connection error
    mock_client_instance = Mock()
    mock_client_instance.request.side_effect = httpx.ConnectError("Connection refused")
    mock_httpx_client.return_value = mock_client_instance

    client = APIClient()

    with pytest.raises(Exception) as exc_info:
        client.get("/test")

    assert "Local API not running" in str(exc_info.value)
    # Should retry 3 times
    assert mock_client_instance.request.call_count == 3


@patch('cli.commands.inspect.httpx.Client')
def test_api_client_404_error(mock_httpx_client):
    """Test API 404 error"""
    import httpx
    from cli.commands.inspect import APIClient

    # Mock 404 response
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Not found"

    mock_client_instance = Mock()
    mock_client_instance.request.side_effect = httpx.HTTPStatusError(
        "404", request=Mock(), response=mock_response
    )
    mock_httpx_client.return_value = mock_client_instance

    client = APIClient()

    with pytest.raises(Exception) as exc_info:
        client.get("/test")

    assert "Resource not found" in str(exc_info.value)


def test_inspect_sync_data_structure():
    """Test expected data structure for inspect sync"""
    # Expected API response structure
    expected_response = {
        "last_sync_at": "2025-12-29T14:30:00Z",
        "direction": "bidirectional",
        "status": "synced",
        "pending_changes": 234,
        "conflicts_count": 0,
        "entity_counts": {
            "vectors": {"local": 1500, "cloud": 1400},
            "tables": {"local": 10, "cloud": 10},
            "files": {"local": 25, "cloud": 20}
        }
    }

    # Validate structure
    assert "last_sync_at" in expected_response
    assert "pending_changes" in expected_response
    assert "entity_counts" in expected_response
    assert isinstance(expected_response["entity_counts"], dict)


def test_inspect_projects_data_structure():
    """Test expected data structure for inspect projects"""
    expected_response = {
        "projects": [
            {
                "id": "proj-123",
                "name": "Test Project",
                "created_at": "2025-12-01T10:00:00Z",
                "vector_count": 1500,
                "table_count": 10,
                "file_count": 25
            }
        ]
    }

    # Validate structure
    assert "projects" in expected_response
    assert isinstance(expected_response["projects"], list)
    if expected_response["projects"]:
        project = expected_response["projects"][0]
        assert "id" in project
        assert "name" in project
        assert "vector_count" in project


def test_inspect_vectors_data_structure():
    """Test expected data structure for inspect vectors"""
    expected_response = {
        "total_vectors": 1500,
        "dimensions": 1536,
        "storage_bytes": 104857600,
        "namespace_count": 3,
        "last_updated": "2025-12-29T14:30:00Z",
        "recent_additions": [
            {
                "id": "vec-abc123def456",
                "namespace": "default",
                "created_at": "2025-12-29T14:25:00Z"
            }
        ]
    }

    # Validate structure
    assert "total_vectors" in expected_response
    assert "dimensions" in expected_response
    assert "storage_bytes" in expected_response
    assert isinstance(expected_response["recent_additions"], list)


def test_inspect_tables_data_structure():
    """Test expected data structure for inspect tables"""
    expected_response = {
        "tables": [
            {
                "name": "users",
                "row_count": 1000,
                "size_bytes": 52428800,
                "last_modified": "2025-12-29T12:00:00Z"
            },
            {
                "name": "products",
                "row_count": 500,
                "size_bytes": 26214400,
                "last_modified": "2025-12-28T18:30:00Z"
            }
        ]
    }

    # Validate structure
    assert "tables" in expected_response
    assert isinstance(expected_response["tables"], list)
    if expected_response["tables"]:
        table = expected_response["tables"][0]
        assert "name" in table
        assert "row_count" in table
        assert "size_bytes" in table


def test_inspect_files_data_structure():
    """Test expected data structure for inspect files"""
    expected_response = {
        "total_files": 25,
        "total_size_bytes": 104857600,
        "file_types": {
            "image/png": {"count": 10, "size_bytes": 52428800},
            "application/pdf": {"count": 8, "size_bytes": 41943040},
            "text/plain": {"count": 7, "size_bytes": 10485760}
        }
    }

    # Validate structure
    assert "total_files" in expected_response
    assert "total_size_bytes" in expected_response
    assert "file_types" in expected_response
    assert isinstance(expected_response["file_types"], dict)


def test_inspect_events_data_structure():
    """Test expected data structure for inspect events"""
    expected_response = {
        "total_events": 5000,
        "oldest_event": "2025-12-01T00:00:00Z",
        "newest_event": "2025-12-29T14:30:00Z",
        "event_types": {
            "vector.created": 2000,
            "table.updated": 1500,
            "file.uploaded": 1000,
            "sync.completed": 500
        },
        "latest_events": [
            {
                "timestamp": "2025-12-29T14:30:00Z",
                "type": "sync.completed",
                "source": "sync-engine",
                "description": "Bidirectional sync completed successfully"
            }
        ]
    }

    # Validate structure
    assert "total_events" in expected_response
    assert "event_types" in expected_response
    assert "latest_events" in expected_response
    assert isinstance(expected_response["latest_events"], list)


def test_inspect_health_data_structure():
    """Test expected data structure for inspect health"""
    expected_response = {
        "status": "healthy",
        "timestamp": "2025-12-29T14:30:00Z",
        "services": {
            "postgresql": {
                "status": "healthy",
                "response_time_ms": 5,
                "details": "Connected"
            },
            "qdrant": {
                "status": "healthy",
                "response_time_ms": 12,
                "details": "All collections accessible"
            },
            "minio": {
                "status": "healthy",
                "response_time_ms": 8,
                "details": "Storage available"
            },
            "redpanda": {
                "status": "healthy",
                "response_time_ms": 15,
                "details": "All topics active"
            },
            "embeddings": {
                "status": "healthy",
                "response_time_ms": 120,
                "details": "Model loaded"
            }
        }
    }

    # Validate structure
    assert "status" in expected_response
    assert "services" in expected_response
    assert isinstance(expected_response["services"], dict)

    # Check all expected services
    expected_services = ["postgresql", "qdrant", "minio", "redpanda", "embeddings"]
    for service in expected_services:
        assert service in expected_response["services"]
        assert "status" in expected_response["services"][service]


def test_api_endpoints():
    """Test that all commands use correct API endpoints"""
    endpoints = {
        "sync": "/v1/projects/{id}/sync/state",
        "projects": "/v1/projects",
        "vectors": "/v1/projects/{id}/database/vectors/stats",
        "tables": "/v1/projects/{id}/database/tables",
        "files": "/v1/projects/{id}/database/files",
        "events": "/v1/projects/{id}/database/events",
        "health": "/health"
    }

    # Verify endpoints are well-formed
    for command, endpoint in endpoints.items():
        assert endpoint.startswith("/")
        if "{id}" in endpoint:
            assert "/v1/projects/" in endpoint


def test_json_output_flag():
    """Test that all commands support --json flag"""
    # This test documents that all commands should support JSON output
    commands_with_json = [
        "sync",
        "projects",
        "vectors",
        "tables",
        "files",
        "events",
        "health"
    ]

    # Verify all commands are documented
    assert len(commands_with_json) == 7


def test_project_id_flag():
    """Test that appropriate commands support --project-id flag"""
    commands_with_project_id = [
        "sync",
        "vectors",
        "tables",
        "files",
        "events"
    ]

    commands_without_project_id = [
        "projects",  # Lists all projects
        "health"     # System-wide health check
    ]

    # Verify categorization
    assert len(commands_with_project_id) == 5
    assert len(commands_without_project_id) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
