"""
Test Projects Router
Integration tests for project CRUD operations
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.mark.integration
class TestProjectsEndpoints:
    """Test suite for projects endpoints"""

    def test_create_project_success(self, client: TestClient, sample_project_data):
        """Test creating a new project"""
        response = client.post("/v1/projects", json=sample_project_data)

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == sample_project_data["name"]
        assert data["description"] == sample_project_data["description"]
        assert "created_at" in data

    def test_create_project_duplicate_name(self, client: TestClient, sample_project_data):
        """Test creating project with duplicate name fails"""
        # Create first project
        client.post("/v1/projects", json=sample_project_data)

        # Try to create duplicate
        response = client.post("/v1/projects", json=sample_project_data)

        assert response.status_code == 409  # Conflict
        data = response.json()
        assert "error" in data
        assert data["error"] == "conflict_error"

    def test_create_project_missing_name(self, client: TestClient):
        """Test creating project without name fails"""
        invalid_data = {
            "description": "Missing name field"
        }

        response = client.post("/v1/projects", json=invalid_data)

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"] == "validation_error"

    def test_list_projects(self, client: TestClient, sample_project_data):
        """Test listing all projects"""
        # Create test projects
        client.post("/v1/projects", json=sample_project_data)

        project_2 = sample_project_data.copy()
        project_2["name"] = "Test Project 2"
        client.post("/v1/projects", json=project_2)

        # List projects
        response = client.get("/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_list_projects_with_pagination(self, client: TestClient, sample_project_data):
        """Test listing projects with pagination"""
        # Create 3 projects
        for i in range(3):
            project = sample_project_data.copy()
            project["name"] = f"Test Project {i+1}"
            client.post("/v1/projects", json=project)

        # Get first page (limit=2)
        response = client.get("/v1/projects?skip=0&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Get second page
        response = client.get("/v1/projects?skip=2&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_get_project_by_id(self, client: TestClient, sample_project_data):
        """Test getting a project by ID"""
        # Create project
        create_response = client.post("/v1/projects", json=sample_project_data)
        project_id = create_response.json()["id"]

        # Get project
        response = client.get(f"/v1/projects/{project_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == sample_project_data["name"]

    def test_get_project_not_found(self, client: TestClient):
        """Test getting non-existent project returns 404"""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = client.get(f"/v1/projects/{fake_id}")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"] == "not_found_error"

    def test_update_project(self, client: TestClient, sample_project_data):
        """Test updating a project"""
        # Create project
        create_response = client.post("/v1/projects", json=sample_project_data)
        project_id = create_response.json()["id"]

        # Update project
        update_data = {
            "name": "Updated Project Name",
            "description": "Updated description"
        }
        response = client.patch(f"/v1/projects/{project_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]

    def test_update_project_not_found(self, client: TestClient):
        """Test updating non-existent project returns 404"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        update_data = {"name": "New Name"}

        response = client.patch(f"/v1/projects/{fake_id}", json=update_data)

        assert response.status_code == 404

    def test_delete_project(self, client: TestClient, sample_project_data):
        """Test deleting a project (soft delete)"""
        # Create project
        create_response = client.post("/v1/projects", json=sample_project_data)
        project_id = create_response.json()["id"]

        # Delete project
        response = client.delete(f"/v1/projects/{project_id}")

        assert response.status_code == 204

        # Verify project is no longer accessible
        get_response = client.get(f"/v1/projects/{project_id}")
        assert get_response.status_code == 404

    def test_delete_project_not_found(self, client: TestClient):
        """Test deleting non-existent project returns 404"""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = client.delete(f"/v1/projects/{fake_id}")

        assert response.status_code == 404

    def test_project_stats(self, client: TestClient, sample_project_data):
        """Test getting project statistics"""
        # Create project
        create_response = client.post("/v1/projects", json=sample_project_data)
        project_id = create_response.json()["id"]

        # Get stats
        response = client.get(f"/v1/projects/{project_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert "vector_count" in data
        assert "memory_count" in data
        assert "table_count" in data
        assert "file_count" in data
        assert "event_count" in data

    def test_create_project_with_settings(self, client: TestClient):
        """Test creating project with custom settings"""
        project_data = {
            "name": "Project with Settings",
            "description": "Testing custom settings",
            "settings": {
                "embedding_model": "custom-model",
                "vector_dimensions": 512,
                "enable_quantum": True
            }
        }

        response = client.post("/v1/projects", json=project_data)

        assert response.status_code == 201
        data = response.json()
        assert data["settings"]["vector_dimensions"] == 512
        assert data["settings"]["enable_quantum"] is True


@pytest.mark.slow
class TestProjectsPerformance:
    """Performance tests for projects endpoints"""

    def test_create_multiple_projects_performance(self, client: TestClient):
        """Test creating 10 projects performance"""
        import time

        project_ids = []
        start_time = time.time()

        for i in range(10):
            project_data = {
                "name": f"Performance Test Project {i}",
                "description": f"Project {i} for performance testing"
            }
            response = client.post("/v1/projects", json=project_data)
            assert response.status_code == 201
            project_ids.append(response.json()["id"])

        end_time = time.time()
        elapsed = end_time - start_time

        # Should complete in under 5 seconds
        assert elapsed < 5.0, f"Creating 10 projects took {elapsed:.2f}s (expected <5s)"

        # Cleanup
        for project_id in project_ids:
            client.delete(f"/v1/projects/{project_id}")
