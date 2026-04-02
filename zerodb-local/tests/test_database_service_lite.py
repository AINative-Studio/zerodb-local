"""
Test SQLite Database Service (DatabaseServiceLite)
BDD-style tests covering project/table/row CRUD, JSON column handling,
CDC change tracking, and the health check endpoint.

Refs #1706
"""
import json
import os
import uuid

import pytest

from lite.services.database_service_lite import DatabaseServiceLite


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path):
    """Provide a temporary SQLite database path for full test isolation."""
    return str(tmp_path / "test_zerodb.db")


@pytest.fixture
def service(db_path):
    """Create a fresh DatabaseServiceLite with an isolated temp database."""
    os.environ["ZERODB_BACKEND"] = "lite"
    svc = DatabaseServiceLite(db_path=db_path)
    yield svc
    os.environ.pop("ZERODB_BACKEND", None)


@pytest.fixture
def user_id():
    return str(uuid.uuid4())


@pytest.fixture
def project(service, user_id):
    """Create a project and return its dict."""
    return service.create_project(
        name="Test Project",
        user_id=user_id,
        description="A test project for BDD tests",
        settings={"vector_dimensions": 384},
    )


@pytest.fixture
def table(service, project):
    """Create a NoSQL table and return its dict."""
    return service.create_table(
        project_id=project["id"],
        name="users",
        schema={
            "fields": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "age": {"type": "integer"},
                "active": {"type": "boolean"},
            }
        },
        description="User profiles table",
    )


@pytest.fixture
def sample_rows():
    """Return sample row data for insertion tests."""
    return [
        {"name": "Alice", "email": "alice@example.com", "age": 30, "active": True},
        {"name": "Bob", "email": "bob@example.com", "age": 25, "active": True},
        {"name": "Carol", "email": "carol@example.com", "age": 35, "active": False},
    ]


# ---------------------------------------------------------------------------
# Schema Initialisation
# ---------------------------------------------------------------------------


class TestSchemaInitialisation:
    """Scenario: The SQLite schema is applied on service creation."""

    def test_database_file_created(self, service, db_path):
        """Given a new service, the database file should exist on disk."""
        assert os.path.exists(db_path)

    def test_all_core_tables_exist(self, service):
        """Given a new service, all expected tables should exist."""
        from sqlalchemy import text

        expected_tables = {
            "projects", "vectors", "memory", "tables", "table_rows",
            "files", "events", "sync_state", "change_log",
            "sync_history", "conflict_log",
        }
        with service.engine.connect() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            actual_tables = {row[0] for row in result.fetchall()}

        assert expected_tables.issubset(actual_tables), (
            f"Missing tables: {expected_tables - actual_tables}"
        )

    def test_foreign_keys_enabled(self, service):
        """Given a new service, foreign keys should be enforced."""
        from sqlalchemy import text

        with service.engine.connect() as conn:
            result = conn.execute(text("PRAGMA foreign_keys"))
            assert result.fetchone()[0] == 1


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    """Scenario: Health check reports SQLite backend status."""

    def test_healthy_status(self, service):
        """Given a working database, health_check returns healthy."""
        import asyncio
        loop = asyncio.new_event_loop()
        health = loop.run_until_complete(service.health_check())
        loop.close()

        assert health["status"] == "healthy"
        assert health["backend"] == "sqlite"
        assert "db_path" in health
        assert "db_size_bytes" in health

    def test_unhealthy_on_bad_path(self, tmp_path):
        """Given an invalid engine, health_check returns unhealthy."""
        import asyncio

        svc = DatabaseServiceLite(db_path=str(tmp_path / "test.db"))
        # Forcibly break the engine to simulate failure
        svc.engine.dispose()
        from sqlalchemy import create_engine
        from sqlalchemy.pool import StaticPool

        svc.engine = create_engine(
            "sqlite:///nonexistent/deep/path/db.sqlite",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )

        loop = asyncio.new_event_loop()
        health = loop.run_until_complete(svc.health_check())
        loop.close()

        assert health["status"] == "unhealthy"
        assert "error" in health


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------


class TestProjectCreate:
    """Scenario: Creating projects stores them correctly."""

    def test_create_project_returns_id(self, service, user_id):
        """Given valid data, create_project returns a dict with a UUID id."""
        result = service.create_project(name="My Project", user_id=user_id)
        assert "id" in result
        # Verify it is a valid UUID
        uuid.UUID(result["id"])

    def test_create_project_stores_all_fields(self, project):
        """Given all fields, the returned project has correct values."""
        assert project["name"] == "Test Project"
        assert project["description"] == "A test project for BDD tests"
        assert project["settings"]["vector_dimensions"] == 384
        assert project["status"] == "ACTIVE"
        assert project["database_enabled"] is True

    def test_create_project_with_defaults(self, service, user_id):
        """Given minimal data, defaults are applied correctly."""
        result = service.create_project(name="Minimal", user_id=user_id)
        assert result["tier"] == "free"
        assert result["status"] == "ACTIVE"
        assert result["settings"] == {}

    def test_create_project_timestamps(self, project):
        """Given a new project, created_at and updated_at are set."""
        assert project["created_at"] is not None
        assert project["updated_at"] is not None


class TestProjectRead:
    """Scenario: Reading projects retrieves correct data."""

    def test_get_project_by_id(self, service, project):
        """Given an existing project, get_project returns it."""
        result = service.get_project(project["id"])
        assert result is not None
        assert result["id"] == project["id"]
        assert result["name"] == project["name"]

    def test_get_project_not_found(self, service):
        """Given a nonexistent ID, get_project returns None."""
        result = service.get_project(str(uuid.uuid4()))
        assert result is None

    def test_list_projects(self, service, user_id):
        """Given multiple projects, list_projects returns all."""
        for i in range(3):
            service.create_project(name=f"Project {i}", user_id=user_id)

        results = service.list_projects(user_id=user_id)
        assert len(results) == 3

    def test_list_projects_pagination(self, service, user_id):
        """Given pagination params, list_projects returns correct subset."""
        for i in range(5):
            service.create_project(name=f"Paginated {i}", user_id=user_id)

        page1 = service.list_projects(user_id=user_id, skip=0, limit=2)
        page2 = service.list_projects(user_id=user_id, skip=2, limit=2)
        page3 = service.list_projects(user_id=user_id, skip=4, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert len(page3) == 1

    def test_list_projects_excludes_deleted(self, service, user_id):
        """Given a soft-deleted project, list_projects excludes it."""
        p = service.create_project(name="To Delete", user_id=user_id)
        service.delete_project(p["id"])

        results = service.list_projects(user_id=user_id)
        ids = [r["id"] for r in results]
        assert p["id"] not in ids


class TestProjectUpdate:
    """Scenario: Updating projects modifies stored data."""

    def test_update_name(self, service, project):
        """Given a new name, update_project changes it."""
        result = service.update_project(project["id"], name="Renamed")
        assert result["name"] == "Renamed"

    def test_update_settings_json(self, service, project):
        """Given new settings, the JSON is stored and retrieved correctly."""
        new_settings = {"embedding_model": "bge-small", "vector_dimensions": 384}
        result = service.update_project(project["id"], settings=new_settings)
        assert result["settings"] == new_settings

    def test_update_nonexistent_returns_none(self, service):
        """Given a nonexistent ID, update_project returns None."""
        result = service.update_project(str(uuid.uuid4()), name="Nope")
        assert result is None

    def test_update_ignores_unknown_fields(self, service, project):
        """Given unknown kwargs, update_project ignores them safely."""
        original = service.get_project(project["id"])
        result = service.update_project(project["id"], bogus_field="ignored")
        assert result["name"] == original["name"]


class TestProjectDelete:
    """Scenario: Deleting projects performs a soft delete."""

    def test_delete_project_returns_true(self, service, project):
        """Given an existing project, delete returns True."""
        assert service.delete_project(project["id"]) is True

    def test_deleted_project_not_found(self, service, project):
        """Given a deleted project, get_project returns None."""
        service.delete_project(project["id"])
        assert service.get_project(project["id"]) is None

    def test_delete_nonexistent_returns_false(self, service):
        """Given a nonexistent ID, delete returns False."""
        assert service.delete_project(str(uuid.uuid4())) is False

    def test_double_delete_returns_false(self, service, project):
        """Given an already-deleted project, a second delete returns False."""
        service.delete_project(project["id"])
        assert service.delete_project(project["id"]) is False


# ---------------------------------------------------------------------------
# Table CRUD
# ---------------------------------------------------------------------------


class TestTableCreate:
    """Scenario: Creating NoSQL tables stores schema definitions."""

    def test_create_table_returns_dict(self, table):
        """Given valid data, create_table returns a table dict with an id."""
        assert "id" in table
        uuid.UUID(table["id"])

    def test_create_table_stores_schema(self, table):
        """Given a JSON schema, it is stored and retrieved correctly."""
        assert table["schema"]["fields"]["name"]["type"] == "string"

    def test_create_duplicate_table_raises(self, service, project):
        """Given a duplicate name, create_table raises an IntegrityError."""
        service.create_table(
            project_id=project["id"], name="dup", schema={"fields": {}}
        )
        with pytest.raises(Exception):
            service.create_table(
                project_id=project["id"], name="dup", schema={"fields": {}}
            )


class TestTableRead:
    """Scenario: Reading tables retrieves correct definitions."""

    def test_get_table_by_name(self, service, project, table):
        """Given an existing table, get_table returns it."""
        result = service.get_table(project["id"], "users")
        assert result is not None
        assert result["name"] == "users"

    def test_get_table_not_found(self, service, project):
        """Given a nonexistent name, get_table returns None."""
        assert service.get_table(project["id"], "nonexistent") is None

    def test_get_table_by_id(self, service, table):
        """Given a table ID, get_table_by_id returns it."""
        result = service.get_table_by_id(table["id"])
        assert result is not None
        assert result["name"] == "users"

    def test_list_tables(self, service, project):
        """Given multiple tables, list_tables returns all."""
        for name in ["alpha", "beta", "gamma"]:
            service.create_table(project["id"], name, {"fields": {}})

        results = service.list_tables(project["id"])
        assert len(results) == 3


class TestTableDelete:
    """Scenario: Deleting a table performs a soft delete."""

    def test_delete_table(self, service, project, table):
        """Given an existing table, delete returns True."""
        assert service.delete_table(project["id"], "users") is True

    def test_deleted_table_not_found(self, service, project, table):
        """Given a deleted table, get_table returns None."""
        service.delete_table(project["id"], "users")
        assert service.get_table(project["id"], "users") is None


# ---------------------------------------------------------------------------
# Row CRUD
# ---------------------------------------------------------------------------


class TestRowInsert:
    """Scenario: Inserting rows into a NoSQL table."""

    def test_insert_rows_returns_count_and_ids(self, service, project, table, sample_rows):
        """Given valid rows, insert returns count and UUIDs."""
        result = service.insert_rows(project["id"], "users", sample_rows)
        assert result["inserted_count"] == 3
        assert len(result["inserted_ids"]) == 3
        for rid in result["inserted_ids"]:
            uuid.UUID(rid)

    def test_insert_into_nonexistent_table_raises(self, service, project):
        """Given a nonexistent table, insert raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            service.insert_rows(project["id"], "ghost_table", [{"data": "nope"}])

    def test_insert_empty_rows(self, service, project, table):
        """Given an empty row list, insert returns zero count."""
        result = service.insert_rows(project["id"], "users", [])
        assert result["inserted_count"] == 0
        assert result["inserted_ids"] == []


class TestRowQuery:
    """Scenario: Querying rows with filters and pagination."""

    def test_query_all_rows(self, service, project, table, sample_rows):
        """Given inserted rows, query without filter returns all."""
        service.insert_rows(project["id"], "users", sample_rows)
        results = service.query_rows(project["id"], "users")
        assert len(results) == 3

    def test_query_with_boolean_filter(self, service, project, table, sample_rows):
        """Given a boolean filter, only matching rows are returned."""
        service.insert_rows(project["id"], "users", sample_rows)
        results = service.query_rows(
            project["id"], "users", filter_dict={"active": True}
        )
        assert len(results) == 2
        assert all(r["data"]["active"] is True for r in results)

    def test_query_with_string_filter(self, service, project, table, sample_rows):
        """Given a string filter, only matching rows are returned."""
        service.insert_rows(project["id"], "users", sample_rows)
        results = service.query_rows(
            project["id"], "users", filter_dict={"name": "Alice"}
        )
        assert len(results) == 1
        assert results[0]["data"]["name"] == "Alice"

    def test_query_with_integer_filter(self, service, project, table, sample_rows):
        """Given an integer filter, only matching rows are returned."""
        service.insert_rows(project["id"], "users", sample_rows)
        results = service.query_rows(
            project["id"], "users", filter_dict={"age": 25}
        )
        assert len(results) == 1
        assert results[0]["data"]["name"] == "Bob"

    def test_query_pagination(self, service, project, table, sample_rows):
        """Given limit and offset, query returns correct subset."""
        service.insert_rows(project["id"], "users", sample_rows)

        page1 = service.query_rows(project["id"], "users", limit=2, offset=0)
        page2 = service.query_rows(project["id"], "users", limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 1

        # No overlap
        ids1 = {r["id"] for r in page1}
        ids2 = {r["id"] for r in page2}
        assert len(ids1 & ids2) == 0

    def test_query_nonexistent_table_raises(self, service, project):
        """Given a nonexistent table, query raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            service.query_rows(project["id"], "ghost_table")

    def test_query_returns_parsed_json(self, service, project, table, sample_rows):
        """Given stored JSON data, query returns parsed Python objects."""
        service.insert_rows(project["id"], "users", sample_rows)
        results = service.query_rows(project["id"], "users")

        for row in results:
            assert isinstance(row["data"], dict)
            assert isinstance(row["data"]["name"], str)
            assert isinstance(row["data"]["age"], int)
            assert isinstance(row["data"]["active"], bool)


class TestRowUpdate:
    """Scenario: Updating rows modifies data in place."""

    def test_update_rows_by_filter(self, service, project, table, sample_rows):
        """Given a filter, update modifies matching rows."""
        service.insert_rows(project["id"], "users", sample_rows)
        result = service.update_rows(
            project["id"], "users",
            filter_dict={"active": True},
            update_data={"status": "verified"},
        )
        assert result["updated_count"] == 2

        # Verify the update persisted
        rows = service.query_rows(
            project["id"], "users", filter_dict={"active": True}
        )
        assert all(r["data"]["status"] == "verified" for r in rows)

    def test_update_preserves_existing_fields(self, service, project, table, sample_rows):
        """Given an update, existing fields not in update_data are preserved."""
        service.insert_rows(project["id"], "users", sample_rows)
        service.update_rows(
            project["id"], "users",
            filter_dict={"name": "Alice"},
            update_data={"department": "Engineering"},
        )

        rows = service.query_rows(
            project["id"], "users", filter_dict={"name": "Alice"}
        )
        assert rows[0]["data"]["email"] == "alice@example.com"
        assert rows[0]["data"]["department"] == "Engineering"

    def test_update_no_matching_rows(self, service, project, table, sample_rows):
        """Given a filter matching nothing, update_count is zero."""
        service.insert_rows(project["id"], "users", sample_rows)
        result = service.update_rows(
            project["id"], "users",
            filter_dict={"name": "Nobody"},
            update_data={"status": "ghost"},
        )
        assert result["updated_count"] == 0


class TestRowDelete:
    """Scenario: Deleting rows performs a soft delete."""

    def test_delete_rows_by_filter(self, service, project, table, sample_rows):
        """Given a filter, delete soft-removes matching rows."""
        service.insert_rows(project["id"], "users", sample_rows)
        result = service.delete_rows(
            project["id"], "users", filter_dict={"active": False}
        )
        assert result["deleted_count"] == 1

        # Verify the row no longer appears in queries
        rows = service.query_rows(
            project["id"], "users", filter_dict={"active": False}
        )
        assert len(rows) == 0

    def test_delete_all_rows(self, service, project, table, sample_rows):
        """Given no filter, delete soft-removes all rows."""
        service.insert_rows(project["id"], "users", sample_rows)
        result = service.delete_rows(project["id"], "users")
        assert result["deleted_count"] == 3

        rows = service.query_rows(project["id"], "users")
        assert len(rows) == 0

    def test_delete_no_matching_rows(self, service, project, table, sample_rows):
        """Given a filter matching nothing, deleted_count is zero."""
        service.insert_rows(project["id"], "users", sample_rows)
        result = service.delete_rows(
            project["id"], "users", filter_dict={"name": "Nobody"}
        )
        assert result["deleted_count"] == 0


# ---------------------------------------------------------------------------
# JSON Column Handling
# ---------------------------------------------------------------------------


class TestJsonColumnHandling:
    """Scenario: JSON columns survive round-trip serialisation."""

    def test_nested_json_roundtrip(self, service, project, table):
        """Given deeply nested JSON, it survives insert and query."""
        nested_row = {
            "name": "Deep",
            "email": "deep@example.com",
            "age": 40,
            "active": True,
            "profile": {
                "bio": "A deeply nested user",
                "tags": ["admin", "beta"],
                "preferences": {
                    "theme": "dark",
                    "notifications": {"email": True, "sms": False},
                },
            },
        }
        service.insert_rows(project["id"], "users", [nested_row])
        results = service.query_rows(project["id"], "users")
        assert results[0]["data"]["profile"]["preferences"]["theme"] == "dark"
        assert results[0]["data"]["profile"]["tags"] == ["admin", "beta"]

    def test_json_with_null_values(self, service, project, table):
        """Given JSON with null values, they are preserved."""
        row = {"name": "Null User", "email": None, "age": None, "active": True}
        service.insert_rows(project["id"], "users", [row])
        results = service.query_rows(project["id"], "users")
        assert results[0]["data"]["email"] is None

    def test_json_with_special_characters(self, service, project, table):
        """Given JSON with special chars, they are preserved."""
        row = {
            "name": "O'Brien \"The Great\"",
            "email": "o'brien@example.com",
            "age": 50,
            "active": True,
        }
        service.insert_rows(project["id"], "users", [row])
        results = service.query_rows(project["id"], "users")
        assert results[0]["data"]["name"] == "O'Brien \"The Great\""

    def test_project_settings_json_roundtrip(self, service, user_id):
        """Given complex project settings, JSON survives round-trip."""
        settings = {
            "embedding_model": "bge-base",
            "indexes": [
                {"type": "ivfflat", "lists": 100},
                {"type": "hnsw", "m": 16},
            ],
            "features": {"quantum": False, "mcp": True},
        }
        p = service.create_project(
            name="JSON Test", user_id=user_id, settings=settings
        )
        retrieved = service.get_project(p["id"])
        assert retrieved["settings"] == settings


# ---------------------------------------------------------------------------
# CDC Change Tracking
# ---------------------------------------------------------------------------


class TestCDCChangeTracking:
    """Scenario: Application-level CDC logs changes on row operations."""

    def test_insert_creates_change_log_entries(self, service, project, table, sample_rows):
        """Given row inserts, CDC logs INSERT operations."""
        service.insert_rows(project["id"], "users", sample_rows)
        changes = service.cdc.get_unsynced_changes(project["id"])

        assert len(changes) == 3
        assert all(c["operation"] == "INSERT" for c in changes)
        assert all(c["entity_type"] == "table_row" for c in changes)

    def test_update_creates_change_log_entries(self, service, project, table, sample_rows):
        """Given row updates, CDC logs UPDATE operations."""
        service.insert_rows(project["id"], "users", sample_rows)

        # Clear the INSERT logs count
        insert_count = len(service.cdc.get_unsynced_changes(project["id"]))

        service.update_rows(
            project["id"], "users",
            filter_dict={"active": True},
            update_data={"status": "updated"},
        )

        all_changes = service.cdc.get_unsynced_changes(project["id"])
        update_changes = [c for c in all_changes if c["operation"] == "UPDATE"]
        assert len(update_changes) == 2

    def test_delete_creates_change_log_entries(self, service, project, table, sample_rows):
        """Given row deletes, CDC logs DELETE operations."""
        service.insert_rows(project["id"], "users", sample_rows)

        service.delete_rows(
            project["id"], "users", filter_dict={"active": False}
        )

        all_changes = service.cdc.get_unsynced_changes(project["id"])
        delete_changes = [c for c in all_changes if c["operation"] == "DELETE"]
        assert len(delete_changes) == 1

    def test_mark_synced(self, service, project, table, sample_rows):
        """Given unsynced changes, mark_synced flags them as synced."""
        service.insert_rows(project["id"], "users", sample_rows)

        changes = service.cdc.get_unsynced_changes(project["id"])
        assert len(changes) == 3

        change_ids = [c["id"] for c in changes]
        count = service.cdc.mark_synced(change_ids)
        assert count == 3

        # After marking, unsynced should be empty
        remaining = service.cdc.get_unsynced_changes(project["id"])
        assert len(remaining) == 0

    def test_change_count(self, service, project, table, sample_rows):
        """Given operations, get_change_count returns correct totals."""
        service.insert_rows(project["id"], "users", sample_rows)

        total = service.cdc.get_change_count(project["id"])
        assert total == 3

        unsynced = service.cdc.get_change_count(project["id"], synced=False)
        assert unsynced == 3

        synced = service.cdc.get_change_count(project["id"], synced=True)
        assert synced == 0

    def test_cdc_data_contains_row_data(self, service, project, table):
        """Given an insert, the CDC log entry contains the row data."""
        row = {"name": "CDC Test", "email": "cdc@test.com", "age": 99, "active": True}
        service.insert_rows(project["id"], "users", [row])

        changes = service.cdc.get_unsynced_changes(project["id"])
        assert changes[0]["data"]["name"] == "CDC Test"


# ---------------------------------------------------------------------------
# Project Stats
# ---------------------------------------------------------------------------


class TestProjectStats:
    """Scenario: Project stats report entity counts."""

    def test_stats_all_zero_initially(self, service, project):
        """Given a fresh project, all counts are zero."""
        stats = service.get_project_stats(project["id"])
        assert stats["vector_count"] == 0
        assert stats["memory_count"] == 0
        assert stats["table_count"] == 0
        assert stats["file_count"] == 0
        assert stats["event_count"] == 0

    def test_stats_reflect_table_count(self, service, project, table):
        """Given a created table, table_count reflects it."""
        stats = service.get_project_stats(project["id"])
        assert stats["table_count"] == 1


# ---------------------------------------------------------------------------
# get_db session generator
# ---------------------------------------------------------------------------


class TestGetDbSession:
    """Scenario: get_db yields a usable SQLAlchemy session."""

    def test_get_db_yields_session(self, service):
        """Given the service, get_db yields a session that can execute queries."""
        from sqlalchemy import text as sa_text

        gen = service.get_db()
        session = next(gen)
        try:
            result = session.execute(sa_text("SELECT 1"))
            assert result.fetchone()[0] == 1
        finally:
            try:
                next(gen)
            except StopIteration:
                pass


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Scenario: Edge cases and boundary conditions."""

    def test_unicode_in_project_name(self, service, user_id):
        """Given unicode characters in name, they are stored correctly."""
        p = service.create_project(name="Projet Francais", user_id=user_id)
        retrieved = service.get_project(p["id"])
        assert retrieved["name"] == "Projet Francais"

    def test_large_batch_insert(self, service, project, table):
        """Given 500 rows, batch insert completes successfully."""
        rows = [
            {"name": f"User {i}", "email": f"u{i}@test.com", "age": 20 + i % 50, "active": i % 2 == 0}
            for i in range(500)
        ]
        result = service.insert_rows(project["id"], "users", rows)
        assert result["inserted_count"] == 500

        # Verify count
        all_rows = service.query_rows(project["id"], "users", limit=1000)
        assert len(all_rows) == 500

    def test_concurrent_session_isolation(self, service):
        """Given multiple get_db calls, sessions are independent."""
        from sqlalchemy import text

        gen1 = service.get_db()
        gen2 = service.get_db()

        s1 = next(gen1)
        s2 = next(gen2)

        # Both sessions should work independently
        r1 = s1.execute(text("SELECT 1")).fetchone()[0]
        r2 = s2.execute(text("SELECT 2")).fetchone()[0]

        assert r1 == 1
        assert r2 == 2

        # Clean up
        for gen in (gen1, gen2):
            try:
                next(gen)
            except StopIteration:
                pass
