"""
Tests for Qdrant Health Check Fix (Issue #1126)
"""
import pytest
import yaml
import os


class TestQdrantDockerCompose:
    """Test Qdrant docker-compose configuration"""

    @pytest.fixture
    def docker_compose_config(self):
        """Load docker-compose.yml"""
        compose_path = os.path.join(
            os.path.dirname(__file__),
            '../../docker-compose.yml'
        )
        with open(compose_path, 'r') as f:
            return yaml.safe_load(f)

    def test_qdrant_has_no_healthcheck(self, docker_compose_config):
        """Verify Qdrant service has no healthcheck configured"""
        qdrant_service = docker_compose_config['services']['qdrant']

        # Healthcheck should not exist
        assert 'healthcheck' not in qdrant_service, \
            "Qdrant should not have healthcheck - image doesn't include curl/wget"

    def test_api_uses_service_started_for_qdrant(self, docker_compose_config):
        """Verify zerodb-api uses service_started condition for Qdrant"""
        api_service = docker_compose_config['services']['zerodb-api']
        depends_on = api_service.get('depends_on', {})

        # Check Qdrant dependency
        assert 'qdrant' in depends_on, "API should depend on Qdrant"

        qdrant_condition = depends_on['qdrant'].get('condition')
        assert qdrant_condition == 'service_started', \
            f"Expected 'service_started', got '{qdrant_condition}'"

    def test_qdrant_service_configured_correctly(self, docker_compose_config):
        """Verify Qdrant service has all required configuration"""
        qdrant = docker_compose_config['services']['qdrant']

        # Check image
        assert qdrant['image'] == 'qdrant/qdrant:latest'

        # Check ports
        assert '6333:6333' in qdrant['ports']  # REST API
        assert '6334:6334' in qdrant['ports']  # gRPC API

        # Check environment
        env = qdrant.get('environment', [])
        assert 'QDRANT__SERVICE__GRPC_PORT=6334' in env

    def test_other_services_still_use_health_checks(self, docker_compose_config):
        """Verify other services still use proper health checks"""
        api_service = docker_compose_config['services']['zerodb-api']
        depends_on = api_service.get('depends_on', {})

        # These services should still use service_healthy
        healthy_services = ['postgres', 'minio', 'redpanda', 'embeddings']

        for service in healthy_services:
            if service in depends_on:
                condition = depends_on[service].get('condition')
                assert condition == 'service_healthy', \
                    f"{service} should use 'service_healthy', got '{condition}'"
