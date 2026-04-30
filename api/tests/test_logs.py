"""
Tests for Logs Router
Validates log retrieval, filtering, and display functionality
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta


@pytest.mark.asyncio
class TestLogsRouter:
    """Test suite for logs endpoints"""

    def test_get_logs_without_filters(self, client: TestClient):
        """Test fetching logs without any filters"""
        response = client.get("/v1/logs")

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "logs" in data
        assert "total_count" in data
        assert "time_range_start" in data
        assert "time_range_end" in data
        assert isinstance(data["logs"], list)
        assert isinstance(data["total_count"], int)

        # Validate each log entry
        if data["logs"]:
            log = data["logs"][0]
            assert "timestamp" in log
            assert "level" in log
            assert "service" in log
            assert "message" in log

    def test_get_logs_with_service_filter(self, client: TestClient):
        """Test filtering logs by service"""
        services = ["postgres", "qdrant", "minio", "redpanda", "embeddings", "api", "dashboard"]

        for service in services:
            response = client.get(f"/v1/logs?service={service}")

            assert response.status_code == 200
            data = response.json()

            assert data["service"] == service

            # All logs should be from the specified service
            for log in data["logs"]:
                assert log["service"] == service

    def test_get_logs_with_level_filter(self, client: TestClient):
        """Test filtering logs by level"""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in levels:
            response = client.get(f"/v1/logs?level={level}")

            assert response.status_code == 200
            data = response.json()

            assert data["level"] == level

            # All logs should have the specified level
            for log in data["logs"]:
                assert log["level"] == level

    def test_get_logs_with_limit(self, client: TestClient):
        """Test limiting the number of log entries"""
        limits = [10, 50, 100, 250]

        for limit in limits:
            response = client.get(f"/v1/logs?limit={limit}")

            assert response.status_code == 200
            data = response.json()

            # Should not exceed the limit
            assert len(data["logs"]) <= limit

    def test_get_logs_with_time_range(self, client: TestClient):
        """Test filtering logs by time range"""
        time_ranges = [5, 15, 30, 60, 360, 1440]

        for since_minutes in time_ranges:
            response = client.get(f"/v1/logs?since_minutes={since_minutes}")

            assert response.status_code == 200
            data = response.json()

            # Parse time range
            time_start = datetime.fromisoformat(data["time_range_start"])
            time_end = datetime.fromisoformat(data["time_range_end"])

            # Validate time range is approximately correct (allow 5 second tolerance)
            expected_duration = timedelta(minutes=since_minutes)
            actual_duration = time_end - time_start

            assert abs((actual_duration - expected_duration).total_seconds()) < 5

    def test_get_logs_with_multiple_filters(self, client: TestClient):
        """Test combining multiple filters"""
        response = client.get("/v1/logs?service=postgres&level=INFO&limit=50&since_minutes=30")

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "postgres"
        assert data["level"] == "INFO"
        assert len(data["logs"]) <= 50

        # Validate all logs match filters
        for log in data["logs"]:
            assert log["service"] == "postgres"
            assert log["level"] == "INFO"

    def test_get_logs_validation_errors(self, client: TestClient):
        """Test validation errors for invalid parameters"""
        # Invalid limit (too high)
        response = client.get("/v1/logs?limit=10000")
        assert response.status_code == 422

        # Invalid limit (too low)
        response = client.get("/v1/logs?limit=0")
        assert response.status_code == 422

        # Invalid time range (too high)
        response = client.get("/v1/logs?since_minutes=5000")
        assert response.status_code == 422

        # Invalid time range (too low)
        response = client.get("/v1/logs?since_minutes=0")
        assert response.status_code == 422

    def test_get_available_services(self, client: TestClient):
        """Test getting list of available services"""
        response = client.get("/v1/logs/services")

        assert response.status_code == 200
        services = response.json()

        assert isinstance(services, list)
        assert len(services) == 7

        expected_services = ["postgres", "qdrant", "minio", "redpanda", "embeddings", "api", "dashboard"]
        for service in expected_services:
            assert service in services

    def test_get_log_levels(self, client: TestClient):
        """Test getting list of available log levels"""
        response = client.get("/v1/logs/levels")

        assert response.status_code == 200
        levels = response.json()

        assert isinstance(levels, list)
        assert len(levels) == 5

        expected_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in expected_levels:
            assert level in levels

    def test_log_entry_structure(self, client: TestClient):
        """Test that log entries have the correct structure"""
        response = client.get("/v1/logs?limit=10")

        assert response.status_code == 200
        data = response.json()

        if data["logs"]:
            log = data["logs"][0]

            # Required fields
            assert "timestamp" in log
            assert "level" in log
            assert "service" in log
            assert "message" in log

            # Validate types
            assert isinstance(log["timestamp"], str)
            assert isinstance(log["level"], str)
            assert isinstance(log["service"], str)
            assert isinstance(log["message"], str)

            # Validate timestamp format
            try:
                datetime.fromisoformat(log["timestamp"])
            except ValueError:
                pytest.fail("Invalid timestamp format")

            # Validate level is one of the expected values
            assert log["level"] in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

            # Validate service is one of the expected values
            assert log["service"] in ["postgres", "qdrant", "minio", "redpanda", "embeddings", "api", "dashboard"]

    def test_log_chronological_order(self, client: TestClient):
        """Test that logs are returned in reverse chronological order (newest first)"""
        response = client.get("/v1/logs?limit=20")

        assert response.status_code == 200
        data = response.json()

        if len(data["logs"]) > 1:
            timestamps = [datetime.fromisoformat(log["timestamp"]) for log in data["logs"]]

            # Verify timestamps are in descending order
            for i in range(len(timestamps) - 1):
                assert timestamps[i] >= timestamps[i + 1], "Logs should be in reverse chronological order"

    def test_logs_pagination_with_limit(self, client: TestClient):
        """Test pagination behavior with different limits"""
        # Get all logs
        response_all = client.get("/v1/logs?limit=1000")
        assert response_all.status_code == 200
        all_logs = response_all.json()

        # Get limited logs
        response_limited = client.get("/v1/logs?limit=10")
        assert response_limited.status_code == 200
        limited_logs = response_limited.json()

        # Limited response should have fewer or equal logs
        assert len(limited_logs["logs"]) <= len(all_logs["logs"])
        assert len(limited_logs["logs"]) <= 10

        # If there are more than 10 logs total, limited should have exactly 10
        if all_logs["total_count"] > 10:
            assert len(limited_logs["logs"]) == 10


@pytest.mark.asyncio
class TestLogsIntegration:
    """Integration tests for logs functionality"""

    def test_logs_with_all_services(self, client: TestClient):
        """Test that logs can be retrieved from all services"""
        services = ["postgres", "qdrant", "minio", "redpanda", "embeddings", "api", "dashboard"]

        for service in services:
            response = client.get(f"/v1/logs?service={service}&limit=10")

            assert response.status_code == 200
            data = response.json()

            # Should have logs from the service (using synthetic data)
            assert isinstance(data["logs"], list)

    def test_logs_filtering_combination(self, client: TestClient):
        """Test various filter combinations"""
        test_cases = [
            {"service": "postgres", "level": "INFO"},
            {"service": "qdrant", "limit": 25},
            {"level": "ERROR", "since_minutes": 120},
            {"service": "api", "level": "WARNING", "limit": 10},
        ]

        for params in test_cases:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            response = client.get(f"/v1/logs?{query_string}")

            assert response.status_code == 200
            data = response.json()

            # Validate filters are applied
            for log in data["logs"]:
                if "service" in params:
                    assert log["service"] == params["service"]
                if "level" in params:
                    assert log["level"] == params["level"]
