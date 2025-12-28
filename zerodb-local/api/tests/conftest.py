"""
Pytest Configuration and Fixtures
Provides test database, clients, and fixtures for all tests
"""
import os
import pytest
import uuid
from typing import Generator, Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Set test environment
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "postgresql://zerodb:zerodb123@localhost:5432/zerodb_test"

from main import app
from services.database_service import database_service


# Test database URL
TEST_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://zerodb:zerodb123@localhost:5432/zerodb_test")


@pytest.fixture(scope="session")
def test_engine():
    """
    Create test database engine (session-scoped)
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        echo=False
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db(test_engine) -> Generator[Session, None, None]:
    """
    Create test database session (function-scoped)
    Each test gets a fresh transaction that is rolled back after the test
    """
    connection = test_engine.connect()
    transaction = connection.begin()

    # Create session from connection
    TestSessionLocal = sessionmaker(bind=connection)
    session = TestSessionLocal()

    yield session

    # Rollback transaction after test
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db: Session) -> TestClient:
    """
    Create FastAPI test client with database override
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass

    # Override database dependency
    app.dependency_overrides[database_service.get_db] = override_get_db

    client = TestClient(app)
    yield client

    # Clear overrides
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_project_id() -> str:
    """
    Generate a test project ID
    """
    return str(uuid.uuid4())


@pytest.fixture(scope="function")
def sample_project_data() -> Dict[str, Any]:
    """
    Sample project data for testing
    """
    return {
        "name": "Test Project",
        "description": "A test project for integration testing",
        "settings": {
            "embedding_model": "BAAI/bge-small-en-v1.5",
            "vector_dimensions": 384
        }
    }


@pytest.fixture(scope="function")
def sample_vector_data() -> Dict[str, Any]:
    """
    Sample vector data for testing
    """
    return {
        "vector_embedding": [0.1] * 384,  # 384 dimensions
        "document": "This is a test document for vector operations",
        "metadata": {
            "type": "test",
            "category": "integration_test"
        }
    }


@pytest.fixture(scope="function")
def sample_memory_data() -> Dict[str, Any]:
    """
    Sample memory data for testing
    """
    return {
        "content": "User asked about the weather today",
        "role": "user",
        "agent_id": "test_agent",
        "session_id": "test_session_001",
        "metadata": {
            "timestamp": "2025-12-28T10:00:00Z",
            "context": "conversation"
        }
    }


@pytest.fixture(scope="function")
def sample_event_data() -> Dict[str, Any]:
    """
    Sample event data for testing
    """
    return {
        "event_type": "user_action",
        "event_data": {
            "action": "button_click",
            "button_id": "submit_form",
            "user_id": "user_123"
        },
        "source": "web_app",
        "correlation_id": "corr_001"
    }


@pytest.fixture(scope="function")
def sample_file_data() -> Dict[str, Any]:
    """
    Sample file data for testing (base64-encoded)
    """
    import base64
    content = b"This is a test file content"
    encoded_content = base64.b64encode(content).decode('utf-8')

    return {
        "file_name": "test_file.txt",
        "file_content": encoded_content,
        "content_type": "text/plain",
        "folder": "test_folder",
        "metadata": {
            "uploaded_by": "test_user",
            "purpose": "integration_test"
        }
    }


@pytest.fixture(scope="function")
def sample_table_data() -> Dict[str, Any]:
    """
    Sample NoSQL table data for testing
    """
    return {
        "table_name": "test_users",
        "schema": {
            "fields": {
                "name": {"type": "string", "required": True},
                "email": {"type": "string", "required": True},
                "age": {"type": "integer", "required": False},
                "active": {"type": "boolean", "required": False}
            }
        },
        "description": "Test user data table"
    }


@pytest.fixture(scope="function")
def sample_table_rows() -> list:
    """
    Sample table rows for testing
    """
    return [
        {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "active": True
        },
        {
            "name": "Jane Smith",
            "email": "jane@example.com",
            "age": 25,
            "active": True
        },
        {
            "name": "Bob Johnson",
            "email": "bob@example.com",
            "age": 35,
            "active": False
        }
    ]


@pytest.fixture(autouse=True)
def setup_teardown(db: Session):
    """
    Setup and teardown for each test
    Cleans up test data after each test
    """
    yield

    # Cleanup - delete test data (soft delete)
    try:
        # Clean up projects
        db.execute(text("""
            UPDATE projects
            SET deleted_at = NOW()
            WHERE name LIKE 'Test%' OR description LIKE '%test%'
        """))

        # Clean up vectors
        db.execute(text("""
            UPDATE vectors
            SET deleted_at = NOW()
            WHERE document LIKE '%test%'
        """))

        # Clean up memory
        db.execute(text("""
            DELETE FROM memory
            WHERE session_id LIKE 'test%'
        """))

        # Clean up events
        db.execute(text("""
            DELETE FROM events
            WHERE source LIKE '%test%'
        """))

        # Clean up files metadata
        db.execute(text("""
            UPDATE files
            SET deleted_at = NOW()
            WHERE file_name LIKE 'test%'
        """))

        # Clean up tables
        db.execute(text("""
            UPDATE tables
            SET deleted_at = NOW()
            WHERE name LIKE 'test%'
        """))

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Cleanup error: {e}")


# Pytest configuration
def pytest_configure(config):
    """
    Pytest configuration hook
    """
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_services: mark test as requiring external services"
    )
