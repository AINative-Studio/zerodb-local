"""
Test Files Router
Integration tests for file storage operations
"""
import pytest
import base64
from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.requires_services
class TestFilesEndpoints:
    """Test suite for files endpoints"""

    @pytest.fixture(autouse=True)
    def setup_project(self, client: TestClient, sample_project_data):
        """Create a project for each test"""
        response = client.post("/v1/projects", json=sample_project_data)
        self.project_id = response.json()["id"]

    def test_upload_file(self, client: TestClient, sample_file_data):
        """Test uploading a file"""
        response = client.post(
            f"/v1/projects/{self.project_id}/database/files/upload",
            json=sample_file_data
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["file_name"] == sample_file_data["file_name"]
        assert data["content_type"] == sample_file_data["content_type"]
        assert "size_bytes" in data

    def test_upload_file_invalid_base64(self, client: TestClient):
        """Test uploading file with invalid base64 fails"""
        invalid_data = {
            "file_name": "test.txt",
            "file_content": "not-valid-base64!@#$%^&*",
            "content_type": "text/plain"
        }

        response = client.post(
            f"/v1/projects/{self.project_id}/database/files/upload",
            json=invalid_data
        )

        assert response.status_code == 400

    def test_list_files(self, client: TestClient, sample_file_data):
        """Test listing files"""
        # Upload files
        for i in range(3):
            file_data = sample_file_data.copy()
            file_data["file_name"] = f"test_file_{i}.txt"
            client.post(
                f"/v1/projects/{self.project_id}/database/files/upload",
                json=file_data
            )

        # List files
        response = client.get(
            f"/v1/projects/{self.project_id}/database/files?limit=10"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_list_files_with_folder_filter(self, client: TestClient, sample_file_data):
        """Test listing files filtered by folder"""
        # Upload to different folders
        folders = ["folder_a", "folder_b", "folder_a"]
        for i, folder in enumerate(folders):
            file_data = sample_file_data.copy()
            file_data["file_name"] = f"file_{i}.txt"
            file_data["folder"] = folder
            client.post(
                f"/v1/projects/{self.project_id}/database/files/upload",
                json=file_data
            )

        # Filter by folder_a
        response = client.get(
            f"/v1/projects/{self.project_id}/database/files?folder=folder_a"
        )

        assert response.status_code == 200
        data = response.json()
        assert all("folder_a" in file["file_path"] for file in data)

    def test_list_files_with_content_type_filter(self, client: TestClient):
        """Test listing files filtered by content type"""
        # Upload different file types
        file_types = [
            ("file1.txt", "text/plain"),
            ("file2.json", "application/json"),
            ("file3.txt", "text/plain")
        ]

        for file_name, content_type in file_types:
            file_data = {
                "file_name": file_name,
                "file_content": base64.b64encode(b"content").decode(),
                "content_type": content_type
            }
            client.post(
                f"/v1/projects/{self.project_id}/database/files/upload",
                json=file_data
            )

        # Filter by text/plain
        response = client.get(
            f"/v1/projects/{self.project_id}/database/files?content_type=text/plain"
        )

        assert response.status_code == 200
        data = response.json()
        assert all(file["content_type"] == "text/plain" for file in data)

    def test_download_file(self, client: TestClient, sample_file_data):
        """Test downloading a file"""
        # Upload file
        upload_response = client.post(
            f"/v1/projects/{self.project_id}/database/files/upload",
            json=sample_file_data
        )
        file_id = upload_response.json()["id"]

        # Download file
        response = client.get(
            f"/v1/projects/{self.project_id}/database/files/{file_id}?return_base64=true"
        )

        assert response.status_code == 200
        data = response.json()
        assert "file_content" in data
        assert data["file_name"] == sample_file_data["file_name"]
        assert data["content_type"] == sample_file_data["content_type"]

        # Verify content matches
        assert data["file_content"] == sample_file_data["file_content"]

    def test_get_file_metadata(self, client: TestClient, sample_file_data):
        """Test getting file metadata without downloading"""
        # Upload file
        upload_response = client.post(
            f"/v1/projects/{self.project_id}/database/files/upload",
            json=sample_file_data
        )
        file_id = upload_response.json()["id"]

        # Get metadata
        response = client.get(
            f"/v1/projects/{self.project_id}/database/files/{file_id}/metadata"
        )

        assert response.status_code == 200
        data = response.json()
        assert "file_name" in data
        assert "content_type" in data
        assert "size_bytes" in data
        assert "created_at" in data
        # Should not include file content
        assert "file_content" not in data

    def test_delete_file(self, client: TestClient, sample_file_data):
        """Test deleting a file"""
        # Upload file
        upload_response = client.post(
            f"/v1/projects/{self.project_id}/database/files/upload",
            json=sample_file_data
        )
        file_id = upload_response.json()["id"]

        # Delete file
        response = client.delete(
            f"/v1/projects/{self.project_id}/database/files/{file_id}"
        )

        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(
            f"/v1/projects/{self.project_id}/database/files/{file_id}"
        )
        assert get_response.status_code == 404

    def test_generate_presigned_url(self, client: TestClient, sample_file_data):
        """Test generating presigned URL for file access"""
        # Upload file
        upload_response = client.post(
            f"/v1/projects/{self.project_id}/database/files/upload",
            json=sample_file_data
        )
        file_id = upload_response.json()["id"]

        # Generate presigned URL
        response = client.get(
            f"/v1/projects/{self.project_id}/database/files/{file_id}/url?expiry_hours=24"
        )

        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert "expires_at" in data
        assert "file_id" in data

    def test_presigned_url_expiry_validation(self, client: TestClient, sample_file_data):
        """Test presigned URL expiry validation"""
        # Upload file
        upload_response = client.post(
            f"/v1/projects/{self.project_id}/database/files/upload",
            json=sample_file_data
        )
        file_id = upload_response.json()["id"]

        # Try with invalid expiry (too long)
        response = client.get(
            f"/v1/projects/{self.project_id}/database/files/{file_id}/url?expiry_hours=200"
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data


@pytest.mark.slow
class TestFilesPerformance:
    """Performance tests for file operations"""

    @pytest.fixture(autouse=True)
    def setup_project(self, client: TestClient, sample_project_data):
        """Create a project for each test"""
        response = client.post("/v1/projects", json=sample_project_data)
        self.project_id = response.json()["id"]

    def test_upload_many_files_performance(self, client: TestClient):
        """Test uploading 50 files performance"""
        import time

        content = base64.b64encode(b"Performance test file content").decode()

        start_time = time.time()
        for i in range(50):
            file_data = {
                "file_name": f"perf_test_{i}.txt",
                "file_content": content,
                "content_type": "text/plain"
            }
            response = client.post(
                f"/v1/projects/{self.project_id}/database/files/upload",
                json=file_data
            )
            assert response.status_code == 201

        end_time = time.time()
        elapsed = end_time - start_time

        # Should complete in under 20 seconds
        assert elapsed < 20.0, f"Uploading 50 files took {elapsed:.2f}s (expected <20s)"
