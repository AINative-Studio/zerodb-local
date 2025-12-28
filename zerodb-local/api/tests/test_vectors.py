"""
Test Vectors Router
Integration tests for vector operations
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.requires_services
class TestVectorsEndpoints:
    """Test suite for vector operations endpoints"""

    @pytest.fixture(autouse=True)
    def setup_project(self, client: TestClient, sample_project_data):
        """Create a project for each test"""
        response = client.post("/v1/projects", json=sample_project_data)
        self.project_id = response.json()["id"]

    def test_upsert_vector(self, client: TestClient, sample_vector_data):
        """Test upserting a single vector"""
        response = client.post(
            f"/v1/projects/{self.project_id}/database/vectors/upsert",
            json=sample_vector_data
        )

        assert response.status_code == 201
        data = response.json()
        assert "vector_id" in data
        assert "project_id" in data
        assert data["document"] == sample_vector_data["document"]

    def test_upsert_vector_invalid_dimensions(self, client: TestClient):
        """Test upserting vector with wrong dimensions fails"""
        invalid_data = {
            "vector_embedding": [0.1] * 512,  # Wrong dimension (should be 384)
            "document": "Test document"
        }

        response = client.post(
            f"/v1/projects/{self.project_id}/database/vectors/upsert",
            json=invalid_data
        )

        assert response.status_code == 400

    def test_batch_upsert_vectors(self, client: TestClient, sample_vector_data):
        """Test batch upserting multiple vectors"""
        batch_data = {
            "vectors": [
                {
                    **sample_vector_data,
                    "document": f"Test document {i}"
                }
                for i in range(5)
            ]
        }

        response = client.post(
            f"/v1/projects/{self.project_id}/database/vectors/upsert-batch",
            json=batch_data
        )

        assert response.status_code == 201
        data = response.json()
        assert "inserted_count" in data
        assert data["inserted_count"] == 5
        assert len(data["vector_ids"]) == 5

    def test_search_vectors(self, client: TestClient, sample_vector_data):
        """Test semantic vector search"""
        # First, upsert some vectors
        for i in range(3):
            vector_data = sample_vector_data.copy()
            vector_data["document"] = f"Document about topic {i}"
            client.post(
                f"/v1/projects/{self.project_id}/database/vectors/upsert",
                json=vector_data
            )

        # Search
        search_query = {
            "query_vector": [0.1] * 384,
            "limit": 10,
            "threshold": 0.7
        }

        response = client.post(
            f"/v1/projects/{self.project_id}/database/vectors/search",
            json=search_query
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10
        if len(data) > 0:
            assert "vector_id" in data[0]
            assert "score" in data[0]
            assert "document" in data[0]

    def test_list_vectors(self, client: TestClient, sample_vector_data):
        """Test listing vectors with pagination"""
        # Create vectors
        for i in range(5):
            vector_data = sample_vector_data.copy()
            vector_data["document"] = f"List test document {i}"
            client.post(
                f"/v1/projects/{self.project_id}/database/vectors/upsert",
                json=vector_data
            )

        # List with pagination
        response = client.get(
            f"/v1/projects/{self.project_id}/database/vectors?limit=3&offset=0"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 3

    def test_get_vector_by_id(self, client: TestClient, sample_vector_data):
        """Test getting a vector by ID"""
        # Create vector
        create_response = client.post(
            f"/v1/projects/{self.project_id}/database/vectors/upsert",
            json=sample_vector_data
        )
        vector_id = create_response.json()["vector_id"]

        # Get vector
        response = client.get(
            f"/v1/projects/{self.project_id}/database/vectors/{vector_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["vector_id"] == vector_id
        assert data["document"] == sample_vector_data["document"]

    def test_get_vector_not_found(self, client: TestClient):
        """Test getting non-existent vector returns 404"""
        fake_id = "nonexistent_vector_id"

        response = client.get(
            f"/v1/projects/{self.project_id}/database/vectors/{fake_id}"
        )

        assert response.status_code == 404

    def test_delete_vector(self, client: TestClient, sample_vector_data):
        """Test deleting a vector"""
        # Create vector
        create_response = client.post(
            f"/v1/projects/{self.project_id}/database/vectors/upsert",
            json=sample_vector_data
        )
        vector_id = create_response.json()["vector_id"]

        # Delete vector
        response = client.delete(
            f"/v1/projects/{self.project_id}/database/vectors/{vector_id}"
        )

        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(
            f"/v1/projects/{self.project_id}/database/vectors/{vector_id}"
        )
        assert get_response.status_code == 404

    def test_vector_stats(self, client: TestClient, sample_vector_data):
        """Test getting vector statistics"""
        # Create some vectors
        for i in range(3):
            vector_data = sample_vector_data.copy()
            vector_data["document"] = f"Stats test {i}"
            client.post(
                f"/v1/projects/{self.project_id}/database/vectors/upsert",
                json=vector_data
            )

        # Get stats
        response = client.get(
            f"/v1/projects/{self.project_id}/database/vectors/stats"
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_vectors" in data
        assert "vector_dimensions" in data
        assert data["total_vectors"] >= 3

    def test_search_with_metadata_filter(self, client: TestClient, sample_vector_data):
        """Test vector search with metadata filtering"""
        # Create vectors with different metadata
        for i in range(3):
            vector_data = sample_vector_data.copy()
            vector_data["metadata"] = {"category": f"cat_{i % 2}"}
            client.post(
                f"/v1/projects/{self.project_id}/database/vectors/upsert",
                json=vector_data
            )

        # Search with filter
        search_query = {
            "query_vector": [0.1] * 384,
            "limit": 10,
            "filter_metadata": {"category": "cat_0"}
        }

        response = client.post(
            f"/v1/projects/{self.project_id}/database/vectors/search",
            json=search_query
        )

        assert response.status_code == 200
        data = response.json()
        # All results should have category "cat_0"
        for result in data:
            assert result["metadata"]["category"] == "cat_0"


@pytest.mark.slow
class TestVectorsPerformance:
    """Performance tests for vector operations"""

    @pytest.fixture(autouse=True)
    def setup_project(self, client: TestClient, sample_project_data):
        """Create a project for each test"""
        response = client.post("/v1/projects", json=sample_project_data)
        self.project_id = response.json()["id"]

    def test_batch_upsert_performance(self, client: TestClient, sample_vector_data):
        """Test batch upserting 100 vectors performance"""
        import time

        batch_data = {
            "vectors": [
                {
                    **sample_vector_data,
                    "document": f"Performance test document {i}"
                }
                for i in range(100)
            ]
        }

        start_time = time.time()
        response = client.post(
            f"/v1/projects/{self.project_id}/database/vectors/upsert-batch",
            json=batch_data
        )
        end_time = time.time()

        assert response.status_code == 201
        elapsed = end_time - start_time

        # Should complete in under 10 seconds
        assert elapsed < 10.0, f"Batch upsert took {elapsed:.2f}s (expected <10s)"

    def test_search_performance(self, client: TestClient, sample_vector_data):
        """Test search performance with 1000 vectors"""
        import time

        # Create 1000 vectors
        batch_data = {
            "vectors": [
                {
                    **sample_vector_data,
                    "document": f"Search perf test {i}"
                }
                for i in range(1000)
            ]
        }
        client.post(
            f"/v1/projects/{self.project_id}/database/vectors/upsert-batch",
            json=batch_data
        )

        # Search
        search_query = {
            "query_vector": [0.1] * 384,
            "limit": 10
        }

        start_time = time.time()
        response = client.post(
            f"/v1/projects/{self.project_id}/database/vectors/search",
            json=search_query
        )
        end_time = time.time()

        assert response.status_code == 200
        elapsed = end_time - start_time

        # Search should be very fast (<1 second)
        assert elapsed < 1.0, f"Search took {elapsed:.2f}s (expected <1s)"
