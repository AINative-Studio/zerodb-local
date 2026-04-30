"""
Test Memory Router
Integration tests for agent memory operations
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.requires_services
class TestMemoryEndpoints:
    """Test suite for memory operations endpoints"""

    @pytest.fixture(autouse=True)
    def setup_project(self, client: TestClient, sample_project_data):
        """Create a project for each test"""
        response = client.post("/v1/projects", json=sample_project_data)
        self.project_id = response.json()["id"]

    def test_store_memory(self, client: TestClient, sample_memory_data):
        """Test storing a memory record"""
        response = client.post(
            f"/v1/projects/{self.project_id}/database/memory/store",
            json=sample_memory_data
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["content"] == sample_memory_data["content"]
        assert data["role"] == sample_memory_data["role"]
        assert data["agent_id"] == sample_memory_data["agent_id"]

    def test_store_memory_invalid_role(self, client: TestClient):
        """Test storing memory with invalid role fails"""
        invalid_data = {
            "content": "Test content",
            "role": "invalid_role",  # Should be user, assistant, or system
            "agent_id": "test"
        }

        response = client.post(
            f"/v1/projects/{self.project_id}/database/memory/store",
            json=invalid_data
        )

        assert response.status_code == 400

    def test_search_memory(self, client: TestClient, sample_memory_data):
        """Test semantic memory search"""
        # Store some memories
        for i in range(3):
            memory_data = sample_memory_data.copy()
            memory_data["content"] = f"Memory content about topic {i}"
            client.post(
                f"/v1/projects/{self.project_id}/database/memory/store",
                json=memory_data
            )

        # Search
        search_query = {
            "query": "topic",
            "limit": 5,
            "agent_id": sample_memory_data["agent_id"]
        }

        response = client.post(
            f"/v1/projects/{self.project_id}/database/memory/search",
            json=search_query
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
        if len(data) > 0:
            assert "similarity_score" in data[0]
            assert "content" in data[0]

    def test_get_context_window(self, client: TestClient, sample_memory_data):
        """Test getting context window for a session"""
        session_id = "test_session_context"

        # Store sequential memories
        for i in range(5):
            memory_data = sample_memory_data.copy()
            memory_data["session_id"] = session_id
            memory_data["content"] = f"Message {i}"
            client.post(
                f"/v1/projects/{self.project_id}/database/memory/store",
                json=memory_data
            )

        # Get context window
        response = client.get(
            f"/v1/projects/{self.project_id}/database/memory/context/{session_id}?limit=10"
        )

        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert "total_messages" in data
        assert "estimated_tokens" in data
        assert len(data["messages"]) == 5

    def test_get_context_window_with_token_limit(self, client: TestClient, sample_memory_data):
        """Test context window with max_tokens limit"""
        session_id = "test_session_tokens"

        # Store memories
        for i in range(10):
            memory_data = sample_memory_data.copy()
            memory_data["session_id"] = session_id
            memory_data["content"] = "A" * 1000  # Large content
            client.post(
                f"/v1/projects/{self.project_id}/database/memory/store",
                json=memory_data
            )

        # Get context with token limit
        response = client.get(
            f"/v1/projects/{self.project_id}/database/memory/context/{session_id}?max_tokens=1000"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["estimated_tokens"] <= 1000

    def test_list_sessions(self, client: TestClient, sample_memory_data):
        """Test listing sessions"""
        agent_id = "test_agent_sessions"

        # Create memories in multiple sessions
        for session_num in range(3):
            for msg_num in range(2):
                memory_data = sample_memory_data.copy()
                memory_data["agent_id"] = agent_id
                memory_data["session_id"] = f"session_{session_num}"
                client.post(
                    f"/v1/projects/{self.project_id}/database/memory/store",
                    json=memory_data
                )

        # List sessions
        response = client.get(
            f"/v1/projects/{self.project_id}/database/memory/sessions?agent_id={agent_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_delete_session(self, client: TestClient, sample_memory_data):
        """Test deleting a session"""
        session_id = "test_session_delete"

        # Store memories
        for i in range(3):
            memory_data = sample_memory_data.copy()
            memory_data["session_id"] = session_id
            client.post(
                f"/v1/projects/{self.project_id}/database/memory/store",
                json=memory_data
            )

        # Delete session
        response = client.delete(
            f"/v1/projects/{self.project_id}/database/memory/sessions/{session_id}"
        )

        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(
            f"/v1/projects/{self.project_id}/database/memory/context/{session_id}"
        )
        data = get_response.json()
        assert data["total_messages"] == 0

    def test_search_with_role_filter(self, client: TestClient, sample_memory_data):
        """Test searching with role filter"""
        # Store memories with different roles
        for role in ["user", "assistant", "system"]:
            memory_data = sample_memory_data.copy()
            memory_data["role"] = role
            memory_data["content"] = f"Content from {role}"
            client.post(
                f"/v1/projects/{self.project_id}/database/memory/store",
                json=memory_data
            )

        # Search only user messages
        search_query = {
            "query": "Content",
            "role": "user",
            "limit": 10
        }

        response = client.post(
            f"/v1/projects/{self.project_id}/database/memory/search",
            json=search_query
        )

        assert response.status_code == 200
        data = response.json()
        for result in data:
            assert result["role"] == "user"


@pytest.mark.slow
class TestMemoryPerformance:
    """Performance tests for memory operations"""

    @pytest.fixture(autouse=True)
    def setup_project(self, client: TestClient, sample_project_data):
        """Create a project for each test"""
        response = client.post("/v1/projects", json=sample_project_data)
        self.project_id = response.json()["id"]

    def test_store_many_memories_performance(self, client: TestClient, sample_memory_data):
        """Test storing 100 memories performance"""
        import time

        start_time = time.time()
        for i in range(100):
            memory_data = sample_memory_data.copy()
            memory_data["content"] = f"Performance test memory {i}"
            response = client.post(
                f"/v1/projects/{self.project_id}/database/memory/store",
                json=memory_data
            )
            assert response.status_code == 201

        end_time = time.time()
        elapsed = end_time - start_time

        # Should complete in under 30 seconds
        assert elapsed < 30.0, f"Storing 100 memories took {elapsed:.2f}s (expected <30s)"
