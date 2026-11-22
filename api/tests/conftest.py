"""
Pytest Configuration and Fixtures
Provides test database, clients, and fixtures for all tests

Refs #50: api/tests/ was previously never collected by pytest (not in
testpaths) and couldn't even run standalone. This conftest.py:

1. Adds api/ to sys.path as a root (sys.path shim), matching the bare-import
   convention the rest of api/ (main.py, auth.py, routers/, services/, ...)
   already uses -- and that production actually runs with (api/Dockerfile
   copies api/ to WORKDIR /app and runs `uvicorn main:app` from there). We
   deliberately do NOT convert those modules to `api.`-prefixed imports:
   that convention is load-bearing for the real running service, and 38+
   files inside api/ use it internally, so rewriting it is a large blast
   radius for what is fundamentally a test-wiring issue. This shim is the
   smaller, safer fix (option (b) from the issue).

2. Does NOT force DATABASE_URL to a hardcoded Postgres URL at import time
   the way the original conftest.py did. That forced `is_lite_mode()`
   (lite/config.py's auto-detection) to always resolve to full mode,
   which -- combined with eager engine creation at module-import time in
   api/database.py and api/services/database_service.py (now fixed to be
   lazy, see those files) -- made importing `main` require psycopg2-binary
   (a full-mode-only, `[full]`-extra dependency) even under a plain
   `pip install -e '.[lite,dev]'` install. Instead, DATABASE_URL is left
   alone unless already set in the environment, and the `db`/`client`
   fixtures below detect whether a real Postgres is reachable and skip
   (not error) when it isn't -- so these integration tests run for real
   against docker-compose's Postgres when available (matching this
   package's README/CI setup), and skip cleanly otherwise instead of
   failing every test with a connection error.
"""
import os
import sys
import uuid
from pathlib import Path
from typing import Generator, Dict, Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# --- sys.path shim: make api/ importable as a root (bare-import convention) ---
# Must precede any import of api/'s own bare-import modules (main, database,
# services.*, ...) below -- but third-party imports above don't depend on it.
_API_ROOT = str(Path(__file__).resolve().parent.parent)
if _API_ROOT not in sys.path:
    sys.path.insert(0, _API_ROOT)

# Test environment flag (read by application code that branches on it)
os.environ.setdefault("TESTING", "true")

# These router-level tests hit real endpoints through `client` with no
# auth headers of their own -- they're written against auth.py's
# documented offline-dev escape hatch ("Set ZERODB_AUTH_MODE=local"), which
# returns a fixed mock user (id 00000000-0000-0000-0000-000000000001) with
# no cloud round-trip. Without this, full mode's default AUTH_MODE="cloud"
# makes every request 401 regardless of the DB layer being fixed. Refs #50.
os.environ.setdefault("ZERODB_AUTH_MODE", "local")

# Only default DATABASE_URL to the docker-compose test Postgres if the
# environment didn't already set one -- never clobber a real setting, and
# never force full mode on a lite-only install that has no need of it.
TEST_DATABASE_URL = os.environ.setdefault(
    "DATABASE_URL", "postgresql://zerodb:zerodb123@localhost:5432/zerodb_test"
)

from main import app  # noqa: E402  (must come after the sys.path shim above)
from services.database_service import database_service  # noqa: E402


def _with_psycopg2_driver(url: str) -> str:
    """
    Force the psycopg2 driver, matching api/database.py's own rewrite: a
    bare "postgresql://" scheme resolves to SQLAlchemy 2.x's default
    psycopg (v3) driver, which isn't installed (requirements.txt and the
    `full` extra both install psycopg2-binary, not psycopg). Refs #50.
    """
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def _postgres_reachable(url: str) -> bool:
    """Best-effort check for whether the configured Postgres is up."""
    if not url.startswith("postgresql"):
        return False
    try:
        probe_engine = create_engine(
            _with_psycopg2_driver(url), connect_args={"connect_timeout": 2}
        )
        with probe_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        probe_engine.dispose()
        return True
    except Exception:
        return False


# Computed once per session: avoids a multi-second connection-timeout retry
# per test file when Postgres isn't running.
_POSTGRES_UP = _postgres_reachable(TEST_DATABASE_URL)
_SKIP_REASON = (
    f"Postgres not reachable at {TEST_DATABASE_URL!r} -- this test exercises "
    "a full-mode router through a real Postgres-backed TestClient; start "
    "the stack with `docker-compose up -d postgres` to run it for real. "
    "Refs #50."
)


@pytest.fixture(scope="session")
def test_engine():
    """
    Create test database engine (session-scoped)
    """
    if not _POSTGRES_UP:
        pytest.skip(_SKIP_REASON)

    engine = create_engine(
        _with_psycopg2_driver(TEST_DATABASE_URL),
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
    try:
        connection = test_engine.connect()
    except OperationalError:
        pytest.skip(_SKIP_REASON)
        return
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
def client(db: Session) -> Generator[TestClient, None, None]:
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

    test_client = TestClient(app)
    yield test_client

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
        # events.correlation_id is a UUID column (schema.sql) -- a
        # non-UUID string here fails with psycopg2.errors.
        # InvalidTextRepresentation against a real Postgres. Refs #50.
        "correlation_id": "00000000-0000-0000-0000-0000000c0001"
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


# No autouse cleanup fixture is needed: the `db` fixture above wraps each
# test in a transaction that is rolled back (never committed) once the
# test finishes, which already discards every write a test makes -- the
# soft-delete/DELETE statements an earlier version of this conftest.py ran
# here in a separate autouse fixture were dead weight even before Refs #50
# (same rollback already undid them), and trying to fetch the `db` fixture
# value from a *separate* autouse fixture's own post-yield teardown is
# unsafe: pytest may have already finalized `db` for that test by the time
# this fixture's teardown code runs, depending on fixture registration
# order, raising "fixture value ... not available" instead of cleaning
# anything up.


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
    # Normally registered by test_docker_build_conftest.py's own
    # pytest_configure, but that file is a plain test module (not named
    # `conftest.py`) so pytest never auto-loads it as a plugin -- register
    # here too so test_docker_build.py's markers don't warn as unknown.
    config.addinivalue_line(
        "markers", "docker: mark test as requiring Docker"
    )
    config.addinivalue_line(
        "markers", "requires_docker: mark test as requiring Docker daemon"
    )
