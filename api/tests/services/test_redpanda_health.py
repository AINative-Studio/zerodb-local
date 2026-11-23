"""
Tests for RedPanda Health Check Fix (Issue #1127)

Refs #50: mocks `_admin_client` (the real private attribute
RedPandaService._get_admin_client() lazily caches to and reads from), not
`admin_client` -- the public name doesn't exist on RedPandaService, so
setting it previously created an unrelated instance attribute that
_get_admin_client() never saw, silently defeating the mock.
"""
import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from services.redpanda_service import RedPandaService


class TestRedPandaHealthCheck:
    """Test RedPanda health check functionality"""

    @pytest.fixture
    def redpanda_service(self):
        """Create RedPanda service instance with mocked admin client"""
        with patch.dict('os.environ', {'TESTING': 'true'}):
            service = RedPandaService()
            return service

    @pytest.mark.asyncio
    async def test_health_check_success(self, redpanda_service):
        """Test health check returns healthy status with correct broker count"""
        # Mock the admin client
        mock_broker1 = MagicMock()
        mock_broker2 = MagicMock()
        mock_cluster = MagicMock()
        mock_cluster.brokers.return_value = [mock_broker1, mock_broker2]

        redpanda_service._admin_client = MagicMock()
        redpanda_service._admin_client.list_topics.return_value = ['topic1', 'topic2']
        redpanda_service._admin_client._client.cluster = mock_cluster

        # Call health check
        result = await redpanda_service.health_check()

        # Verify results
        assert result["status"] == "healthy"
        assert result["brokers"] == 2
        assert result["topics"] == ['topic1', 'topic2']
        assert "bootstrap_servers" in result

    @pytest.mark.asyncio
    async def test_health_check_handles_errors(self, redpanda_service):
        """Test health check returns unhealthy status on errors"""
        # Mock admin client to raise exception
        redpanda_service._admin_client = MagicMock()
        redpanda_service._admin_client.list_topics.side_effect = Exception("Connection failed")

        # Call health check
        result = await redpanda_service.health_check()

        # Verify error handling
        assert result["status"] == "unhealthy"
        assert "error" in result
        assert "Connection failed" in result["error"]
