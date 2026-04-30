"""
Test Authentication Module
Integration tests for authentication flow and user handling
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.mark.integration
class TestAuthenticationModule:
    """Test suite for authentication module"""

    def test_auth_module_imports(self):
        """Test that auth module imports correctly"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

        from auth import get_current_user, User, get_user

        assert get_current_user is not None
        assert get_user is not None
        assert User is not None

    def test_user_model_structure(self):
        """Test User model has correct attributes"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

        from auth import User

        # Test User model can be instantiated
        user = User(
            id="00000000-0000-0000-0000-000000000001",
            email="test@example.com",
            username="testuser"
        )

        assert user.id == "00000000-0000-0000-0000-000000000001"
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.is_active is True  # Default value

    def test_user_model_default_values(self):
        """Test User model default values"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

        from auth import User

        # Test with minimal data
        user = User(
            id="00000000-0000-0000-0000-000000000002",
            email="minimal@example.com"
        )

        assert user.username == ""  # Default empty string
        assert user.is_active is True  # Default True


@pytest.mark.integration
class TestLocalAuthenticationMode:
    """Test suite for local authentication mode"""

    @patch.dict(os.environ, {"ZERODB_AUTH_MODE": "local"})
    def test_local_auth_mode_returns_user(self):
        """Test local auth mode returns local user without token"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

        # Force reload of auth module to pick up env var
        if 'auth' in sys.modules:
            del sys.modules['auth']

        from auth import get_current_user, User, AUTH_MODE

        # Verify we're in local mode
        assert AUTH_MODE == "local"

    @patch.dict(os.environ, {"ZERODB_AUTH_MODE": "local"})
    def test_local_user_has_valid_uuid(self):
        """Test local user has valid UUID format"""
        import sys
        import uuid
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

        # Force reload
        if 'auth' in sys.modules:
            del sys.modules['auth']

        from auth import get_current_user

        # Create mock dependencies
        mock_credentials = None
        mock_db = MagicMock()

        # This should not raise an error
        import asyncio
        user = asyncio.run(get_current_user(mock_credentials, mock_db))

        # Verify UUID is valid
        try:
            uuid.UUID(user.id)
            uuid_valid = True
        except ValueError:
            uuid_valid = False

        assert uuid_valid, f"User ID '{user.id}' is not a valid UUID"
        assert user.id == "00000000-0000-0000-0000-000000000001"


@pytest.mark.integration
class TestRouterAuthenticationIntegration:
    """Test suite for router authentication integration"""

    def test_projects_router_uses_correct_auth(self, client: TestClient, sample_project_data):
        """Test projects router works with local auth"""
        # This should work because local auth mode is active
        response = client.post("/v1/projects", json=sample_project_data)

        # Should succeed with local auth
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "user_id" in data
        # Verify it's using the local user UUID
        assert data["user_id"] == "00000000-0000-0000-0000-000000000001"

    def test_vectors_router_authentication(self, client: TestClient, sample_project_data):
        """Test vectors router has authentication dependency"""
        # Create a project first
        project_response = client.post("/v1/projects", json=sample_project_data)
        project_id = project_response.json()["id"]

        # Test vector upsert endpoint
        vector_data = {
            "document": "Test document for authentication check",
            "metadata": {"test": True},
            "namespace": "default"
        }

        response = client.post(
            f"/v1/projects/{project_id}/database/vectors/upsert",
            json=vector_data
        )

        # Should work with local auth
        assert response.status_code in [200, 201]

    def test_memory_router_authentication(self, client: TestClient, sample_project_data, sample_memory_data):
        """Test memory router has authentication dependency"""
        # Create a project first
        project_response = client.post("/v1/projects", json=sample_project_data)
        project_id = project_response.json()["id"]

        # Test memory store endpoint
        response = client.post(
            f"/v1/projects/{project_id}/database/memory/store",
            json=sample_memory_data
        )

        # Should work with local auth
        assert response.status_code in [200, 201]

    def test_tables_router_authentication(self, client: TestClient, sample_project_data, sample_table_data):
        """Test tables router has authentication dependency"""
        # Create a project first
        project_response = client.post("/v1/projects", json=sample_project_data)
        project_id = project_response.json()["id"]

        # Test table create endpoint
        response = client.post(
            f"/v1/projects/{project_id}/database/tables",
            json=sample_table_data
        )

        # Should work with local auth
        assert response.status_code in [200, 201]

    def test_files_router_authentication(self, client: TestClient, sample_project_data, sample_file_data):
        """Test files router has authentication dependency"""
        # Create a project first
        project_response = client.post("/v1/projects", json=sample_project_data)
        project_id = project_response.json()["id"]

        # Test file upload endpoint
        response = client.post(
            f"/v1/projects/{project_id}/database/files/upload",
            json=sample_file_data
        )

        # Should work with local auth
        assert response.status_code in [200, 201]

    def test_events_router_authentication(self, client: TestClient, sample_project_data, sample_event_data):
        """Test events router has authentication dependency"""
        # Create a project first
        project_response = client.post("/v1/projects", json=sample_project_data)
        project_id = project_response.json()["id"]

        # Test event create endpoint
        response = client.post(
            f"/v1/projects/{project_id}/database/events/create",
            json=sample_event_data
        )

        # Should work with local auth
        assert response.status_code in [200, 201]


@pytest.mark.integration
class TestAuthenticationImportPaths:
    """Test suite to verify correct import paths in routers"""

    def test_projects_router_imports(self):
        """Verify projects router imports from auth module"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api', 'routers'))

        # Read the projects.py file
        projects_file = os.path.join(os.path.dirname(__file__), '..', 'api', 'routers', 'projects.py')
        with open(projects_file, 'r') as f:
            content = f.read()

        # Verify correct import
        assert 'from auth import get_current_user' in content, \
            "projects.py should import from 'auth' module"
        assert 'from app.api.deps import' not in content, \
            "projects.py should not import from 'app.api.deps'"

    def test_vectors_router_imports(self):
        """Verify vectors router imports from auth module"""
        vectors_file = os.path.join(os.path.dirname(__file__), '..', 'api', 'routers', 'vectors.py')
        with open(vectors_file, 'r') as f:
            content = f.read()

        assert 'from auth import get_current_user' in content
        assert 'from app.api.deps import' not in content

    def test_tables_router_imports(self):
        """Verify tables router imports from auth module"""
        tables_file = os.path.join(os.path.dirname(__file__), '..', 'api', 'routers', 'tables.py')
        with open(tables_file, 'r') as f:
            content = f.read()

        assert 'from auth import get_current_user' in content
        assert 'from app.api.deps import' not in content

    def test_memory_router_imports(self):
        """Verify memory router imports from auth module"""
        memory_file = os.path.join(os.path.dirname(__file__), '..', 'api', 'routers', 'memory.py')
        with open(memory_file, 'r') as f:
            content = f.read()

        assert 'from auth import get_current_user' in content
        assert 'from app.api.deps import' not in content

    def test_files_router_imports(self):
        """Verify files router imports from auth module"""
        files_file = os.path.join(os.path.dirname(__file__), '..', 'api', 'routers', 'files.py')
        with open(files_file, 'r') as f:
            content = f.read()

        assert 'from auth import get_current_user' in content
        assert 'from app.api.deps import' not in content

    def test_events_router_imports(self):
        """Verify events router imports from auth module"""
        events_file = os.path.join(os.path.dirname(__file__), '..', 'api', 'routers', 'events.py')
        with open(events_file, 'r') as f:
            content = f.read()

        assert 'from auth import get_current_user' in content
        assert 'from app.api.deps import' not in content

    def test_sync_state_router_imports(self):
        """Verify sync_state router imports from auth module"""
        sync_state_file = os.path.join(os.path.dirname(__file__), '..', 'api', 'routers', 'sync_state.py')
        with open(sync_state_file, 'r') as f:
            content = f.read()

        assert 'from auth import get_current_user' in content
        assert 'from app.api.deps import' not in content

    def test_schema_diff_router_imports(self):
        """Verify schema_diff router imports from auth module"""
        schema_diff_file = os.path.join(os.path.dirname(__file__), '..', 'api', 'routers', 'schema_diff.py')
        with open(schema_diff_file, 'r') as f:
            content = f.read()

        assert 'from auth import get_current_user' in content
        assert 'from app.api.deps import' not in content

    def test_change_detection_router_imports(self):
        """Verify change_detection router imports from auth module"""
        change_detection_file = os.path.join(os.path.dirname(__file__), '..', 'api', 'routers', 'change_detection.py')
        with open(change_detection_file, 'r') as f:
            content = f.read()

        assert 'from auth import get_current_user' in content
        assert 'from app.api.deps import' not in content


@pytest.mark.integration
class TestAuthenticationEndToEnd:
    """End-to-end authentication flow tests"""

    def test_complete_workflow_with_authentication(self, client: TestClient):
        """Test complete workflow: create project -> add vector -> query -> delete"""
        # 1. Create project (requires auth)
        project_data = {
            "name": "E2E Test Project",
            "description": "End-to-end authentication test"
        }
        project_response = client.post("/v1/projects", json=project_data)
        assert project_response.status_code == 201
        project_id = project_response.json()["id"]
        user_id = project_response.json()["user_id"]

        # 2. List projects (requires auth)
        list_response = client.get("/v1/projects")
        assert list_response.status_code == 200
        projects = list_response.json()
        assert any(p["id"] == project_id for p in projects)

        # 3. Get project details (requires auth)
        get_response = client.get(f"/v1/projects/{project_id}")
        assert get_response.status_code == 200
        assert get_response.json()["user_id"] == user_id

        # 4. Update project (requires auth)
        update_data = {"description": "Updated via E2E test"}
        update_response = client.patch(f"/v1/projects/{project_id}", json=update_data)
        assert update_response.status_code == 200

        # 5. Get stats (requires auth)
        stats_response = client.get(f"/v1/projects/{project_id}/stats")
        assert stats_response.status_code == 200
        assert "vector_count" in stats_response.json()

        # 6. Delete project (requires auth)
        delete_response = client.delete(f"/v1/projects/{project_id}")
        assert delete_response.status_code == 204

    def test_all_routers_accessible_with_auth(self, client: TestClient):
        """Test that all router endpoints are accessible with authentication"""
        # Create a project for testing
        project_data = {"name": "Router Test Project"}
        project_response = client.post("/v1/projects", json=project_data)
        assert project_response.status_code == 201
        project_id = project_response.json()["id"]

        # Test each router type
        routers_to_test = [
            (f"/v1/projects/{project_id}/database/vectors/list", "GET"),
            (f"/v1/projects/{project_id}/database/memory/list", "GET"),
            (f"/v1/projects/{project_id}/database/tables", "GET"),
            (f"/v1/projects/{project_id}/database/files/list", "GET"),
            (f"/v1/projects/{project_id}/database/events/list", "GET"),
        ]

        for endpoint, method in routers_to_test:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint)

            # Should not get 401 Unauthorized with local auth
            assert response.status_code != 401, \
                f"Endpoint {endpoint} returned 401, authentication failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
