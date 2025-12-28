"""
Test Tables Router
Integration tests for NoSQL table operations
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestTablesEndpoints:
    """Test suite for NoSQL tables endpoints"""

    @pytest.fixture(autouse=True)
    def setup_project(self, client: TestClient, sample_project_data):
        """Create a project for each test"""
        response = client.post("/v1/projects", json=sample_project_data)
        self.project_id = response.json()["id"]

    def test_create_table(self, client: TestClient, sample_table_data):
        """Test creating a NoSQL table"""
        response = client.post(
            f"/v1/projects/{self.project_id}/database/tables",
            json=sample_table_data
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == sample_table_data["table_name"]
        assert data["schema"] == sample_table_data["schema"]

    def test_create_table_duplicate_name(self, client: TestClient, sample_table_data):
        """Test creating table with duplicate name fails"""
        # Create first table
        client.post(
            f"/v1/projects/{self.project_id}/database/tables",
            json=sample_table_data
        )

        # Try to create duplicate
        response = client.post(
            f"/v1/projects/{self.project_id}/database/tables",
            json=sample_table_data
        )

        assert response.status_code == 409

    def test_list_tables(self, client: TestClient, sample_table_data):
        """Test listing tables"""
        # Create tables
        for i in range(3):
            table_data = sample_table_data.copy()
            table_data["table_name"] = f"test_table_{i}"
            client.post(
                f"/v1/projects/{self.project_id}/database/tables",
                json=table_data
            )

        # List tables
        response = client.get(
            f"/v1/projects/{self.project_id}/database/tables?limit=10"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_get_table(self, client: TestClient, sample_table_data):
        """Test getting a table by name"""
        # Create table
        client.post(
            f"/v1/projects/{self.project_id}/database/tables",
            json=sample_table_data
        )

        # Get table
        response = client.get(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_table_data["table_name"]

    def test_get_table_not_found(self, client: TestClient):
        """Test getting non-existent table returns 404"""
        response = client.get(
            f"/v1/projects/{self.project_id}/database/tables/nonexistent_table"
        )

        assert response.status_code == 404

    def test_delete_table(self, client: TestClient, sample_table_data):
        """Test deleting a table"""
        # Create table
        client.post(
            f"/v1/projects/{self.project_id}/database/tables",
            json=sample_table_data
        )

        # Delete table
        response = client.delete(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}"
        )

        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}"
        )
        assert get_response.status_code == 404

    def test_insert_rows(self, client: TestClient, sample_table_data, sample_table_rows):
        """Test inserting rows into table"""
        # Create table
        client.post(
            f"/v1/projects/{self.project_id}/database/tables",
            json=sample_table_data
        )

        # Insert rows
        insert_data = {"rows": sample_table_rows}
        response = client.post(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}/insert",
            json=insert_data
        )

        assert response.status_code == 200
        data = response.json()
        assert "inserted_count" in data
        assert data["inserted_count"] == len(sample_table_rows)
        assert "inserted_ids" in data
        assert len(data["inserted_ids"]) == len(sample_table_rows)

    def test_query_rows(self, client: TestClient, sample_table_data, sample_table_rows):
        """Test querying rows from table"""
        # Create table and insert rows
        client.post(
            f"/v1/projects/{self.project_id}/database/tables",
            json=sample_table_data
        )
        client.post(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}/insert",
            json={"rows": sample_table_rows}
        )

        # Query all rows
        query_data = {"limit": 100, "offset": 0}
        response = client.post(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}/query",
            json=query_data
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == len(sample_table_rows)

    def test_query_rows_with_filter(self, client: TestClient, sample_table_data, sample_table_rows):
        """Test querying rows with JSONB filter"""
        # Create table and insert rows
        client.post(
            f"/v1/projects/{self.project_id}/database/tables",
            json=sample_table_data
        )
        client.post(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}/insert",
            json={"rows": sample_table_rows}
        )

        # Query with filter (active = True)
        query_data = {
            "filter": {"active": True},
            "limit": 100
        }
        response = client.post(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}/query",
            json=query_data
        )

        assert response.status_code == 200
        data = response.json()
        # Should only return rows where active=True
        assert all(row["data"]["active"] is True for row in data)

    def test_query_rows_pagination(self, client: TestClient, sample_table_data, sample_table_rows):
        """Test querying rows with pagination"""
        # Create table and insert rows
        client.post(
            f"/v1/projects/{self.project_id}/database/tables",
            json=sample_table_data
        )
        client.post(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}/insert",
            json={"rows": sample_table_rows}
        )

        # First page
        query_data = {"limit": 2, "offset": 0}
        response = client.post(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}/query",
            json=query_data
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Second page
        query_data = {"limit": 2, "offset": 2}
        response = client.post(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}/query",
            json=query_data
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # Only 3 rows total, so 1 on second page

    def test_update_rows(self, client: TestClient, sample_table_data, sample_table_rows):
        """Test updating rows in table"""
        # Create table and insert rows
        client.post(
            f"/v1/projects/{self.project_id}/database/tables",
            json=sample_table_data
        )
        client.post(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}/insert",
            json={"rows": sample_table_rows}
        )

        # Update rows where active=True
        update_data = {
            "filter": {"active": True},
            "update": {"status": "verified"}
        }
        response = client.put(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}/update",
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert "updated_count" in data
        assert data["updated_count"] == 2  # Two rows have active=True

        # Verify update
        query_response = client.post(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}/query",
            json={"filter": {"active": True}}
        )
        rows = query_response.json()
        assert all(row["data"]["status"] == "verified" for row in rows)

    def test_delete_rows(self, client: TestClient, sample_table_data, sample_table_rows):
        """Test deleting rows from table"""
        # Create table and insert rows
        client.post(
            f"/v1/projects/{self.project_id}/database/tables",
            json=sample_table_data
        )
        client.post(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}/insert",
            json={"rows": sample_table_rows}
        )

        # Delete rows where active=False
        delete_data = {
            "filter": {"active": False}
        }
        response = client.delete(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}/rows",
            json=delete_data
        )

        assert response.status_code == 200
        data = response.json()
        assert "deleted_count" in data
        assert data["deleted_count"] == 1  # One row has active=False

        # Verify deletion
        query_response = client.post(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}/query",
            json={"filter": {"active": False}}
        )
        rows = query_response.json()
        assert len(rows) == 0  # Should be deleted


@pytest.mark.slow
class TestTablesPerformance:
    """Performance tests for table operations"""

    @pytest.fixture(autouse=True)
    def setup_project(self, client: TestClient, sample_project_data):
        """Create a project for each test"""
        response = client.post("/v1/projects", json=sample_project_data)
        self.project_id = response.json()["id"]

    def test_insert_many_rows_performance(self, client: TestClient, sample_table_data):
        """Test inserting 1000 rows performance"""
        import time

        # Create table
        client.post(
            f"/v1/projects/{self.project_id}/database/tables",
            json=sample_table_data
        )

        # Generate 1000 rows
        rows = [
            {
                "name": f"User {i}",
                "email": f"user{i}@example.com",
                "age": 20 + (i % 50),
                "active": i % 2 == 0
            }
            for i in range(1000)
        ]

        start_time = time.time()
        response = client.post(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}/insert",
            json={"rows": rows}
        )
        end_time = time.time()

        assert response.status_code == 200
        elapsed = end_time - start_time

        # Should complete in under 10 seconds
        assert elapsed < 10.0, f"Inserting 1000 rows took {elapsed:.2f}s (expected <10s)"

    def test_query_large_dataset_performance(self, client: TestClient, sample_table_data):
        """Test querying from table with 1000 rows"""
        import time

        # Create table and insert 1000 rows
        client.post(
            f"/v1/projects/{self.project_id}/database/tables",
            json=sample_table_data
        )

        rows = [
            {
                "name": f"User {i}",
                "email": f"user{i}@example.com",
                "age": 20 + (i % 50),
                "active": i % 2 == 0
            }
            for i in range(1000)
        ]
        client.post(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}/insert",
            json={"rows": rows}
        )

        # Query with filter
        query_data = {
            "filter": {"active": True},
            "limit": 100
        }

        start_time = time.time()
        response = client.post(
            f"/v1/projects/{self.project_id}/database/tables/{sample_table_data['table_name']}/query",
            json=query_data
        )
        end_time = time.time()

        assert response.status_code == 200
        elapsed = end_time - start_time

        # Query should be fast (<2 seconds)
        assert elapsed < 2.0, f"Query took {elapsed:.2f}s (expected <2s)"
