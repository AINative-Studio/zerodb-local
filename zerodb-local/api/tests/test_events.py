"""
Test Events Router
Integration tests for event streaming operations
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.requires_services
class TestEventsEndpoints:
    """Test suite for events endpoints"""

    @pytest.fixture(autouse=True)
    def setup_project(self, client: TestClient, sample_project_data):
        """Create a project for each test"""
        response = client.post("/v1/projects", json=sample_project_data)
        self.project_id = response.json()["id"]

    def test_create_event(self, client: TestClient, sample_event_data):
        """Test creating an event"""
        response = client.post(
            f"/v1/projects/{self.project_id}/database/events",
            json=sample_event_data
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["event_type"] == sample_event_data["event_type"]
        assert data["event_data"] == sample_event_data["event_data"]
        assert "created_at" in data

    def test_create_event_missing_type(self, client: TestClient):
        """Test creating event without event_type fails"""
        invalid_data = {
            "event_data": {"key": "value"}
        }

        response = client.post(
            f"/v1/projects/{self.project_id}/database/events",
            json=invalid_data
        )

        assert response.status_code == 400

    def test_list_events(self, client: TestClient, sample_event_data):
        """Test listing events"""
        # Create events
        for i in range(5):
            event_data = sample_event_data.copy()
            event_data["event_data"]["index"] = i
            client.post(
                f"/v1/projects/{self.project_id}/database/events",
                json=event_data
            )

        # List events
        response = client.get(
            f"/v1/projects/{self.project_id}/database/events?limit=10"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 5

    def test_list_events_with_type_filter(self, client: TestClient, sample_event_data):
        """Test listing events filtered by event_type"""
        # Create events of different types
        types = ["type_a", "type_b", "type_a"]
        for event_type in types:
            event_data = sample_event_data.copy()
            event_data["event_type"] = event_type
            client.post(
                f"/v1/projects/{self.project_id}/database/events",
                json=event_data
            )

        # Filter by type_a
        response = client.get(
            f"/v1/projects/{self.project_id}/database/events?event_type=type_a"
        )

        assert response.status_code == 200
        data = response.json()
        assert all(event["event_type"] == "type_a" for event in data)

    def test_list_events_with_source_filter(self, client: TestClient, sample_event_data):
        """Test listing events filtered by source"""
        # Create events from different sources
        sources = ["web_app", "mobile_app", "web_app"]
        for source in sources:
            event_data = sample_event_data.copy()
            event_data["source"] = source
            client.post(
                f"/v1/projects/{self.project_id}/database/events",
                json=event_data
            )

        # Filter by web_app
        response = client.get(
            f"/v1/projects/{self.project_id}/database/events?source=web_app"
        )

        assert response.status_code == 200
        data = response.json()
        assert all(event["source"] == "web_app" for event in data)

    def test_list_events_with_time_range(self, client: TestClient, sample_event_data):
        """Test listing events within time range"""
        from datetime import datetime, timedelta

        # Create event
        client.post(
            f"/v1/projects/{self.project_id}/database/events",
            json=sample_event_data
        )

        # Query with time range
        start_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        end_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()

        response = client.get(
            f"/v1/projects/{self.project_id}/database/events?start_time={start_time}&end_time={end_time}"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_get_event_by_id(self, client: TestClient, sample_event_data):
        """Test getting an event by ID"""
        # Create event
        create_response = client.post(
            f"/v1/projects/{self.project_id}/database/events",
            json=sample_event_data
        )
        event_id = create_response.json()["id"]

        # Get event
        response = client.get(
            f"/v1/projects/{self.project_id}/database/events/{event_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == event_id

    def test_get_event_not_found(self, client: TestClient):
        """Test getting non-existent event returns 404"""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = client.get(
            f"/v1/projects/{self.project_id}/database/events/{fake_id}"
        )

        assert response.status_code == 404

    def test_get_event_stats(self, client: TestClient, sample_event_data):
        """Test getting event statistics"""
        # Create events
        for i in range(10):
            event_data = sample_event_data.copy()
            event_data["event_type"] = f"type_{i % 3}"  # 3 different types
            client.post(
                f"/v1/projects/{self.project_id}/database/events",
                json=event_data
            )

        # Get stats
        response = client.get(
            f"/v1/projects/{self.project_id}/database/events/stats/summary?time_range=day"
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data
        assert "event_type_count" in data
        assert "top_event_types" in data
        assert data["total_events"] >= 10

    def test_subscribe_to_events(self, client: TestClient):
        """Test subscribing to event stream"""
        subscription_data = {
            "event_types": ["user_action", "system_event"]
        }

        response = client.post(
            f"/v1/projects/{self.project_id}/database/events/subscribe",
            json=subscription_data
        )

        assert response.status_code == 201
        data = response.json()
        assert "subscription_id" in data
        assert "topic" in data
        assert data["event_types"] == subscription_data["event_types"]


@pytest.mark.slow
class TestEventsPerformance:
    """Performance tests for event operations"""

    @pytest.fixture(autouse=True)
    def setup_project(self, client: TestClient, sample_project_data):
        """Create a project for each test"""
        response = client.post("/v1/projects", json=sample_project_data)
        self.project_id = response.json()["id"]

    def test_create_many_events_performance(self, client: TestClient, sample_event_data):
        """Test creating 100 events performance"""
        import time

        start_time = time.time()
        for i in range(100):
            event_data = sample_event_data.copy()
            event_data["event_data"]["index"] = i
            response = client.post(
                f"/v1/projects/{self.project_id}/database/events",
                json=event_data
            )
            assert response.status_code == 201

        end_time = time.time()
        elapsed = end_time - start_time

        # Should complete in under 15 seconds
        assert elapsed < 15.0, f"Creating 100 events took {elapsed:.2f}s (expected <15s)"
