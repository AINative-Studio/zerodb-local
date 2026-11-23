"""
Tests for db/pg_migrations.py -- the full-mode (Postgres) schema migration
runner. Refs #121.

Mirrors tests/test_lite_mode_crud.py's
TestSchemaMigrationOfAPreExistingDatabase pattern: seed a database with the
OLD shape these tables actually had (api/db/migrations/001_initial_schema.sql),
run the migration, then assert both the new shape and that pre-existing
data survived the migration.
"""
import os
import sys
import uuid

from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.pg_migrations import apply_pending_migrations  # noqa: E402

# No direct import from conftest.py -- api/tests/ convention (see e.g.
# test_sync_plan_persistence.py) is to depend on its `test_engine`/`db`
# fixtures by name instead, which already handles "skip cleanly if
# Postgres isn't reachable" (conftest.py's _POSTGRES_UP check). This
# module uses `test_engine` rather than `db`: `db` wraps each test in a
# transaction it rolls back afterward, which would fight pg_migrations.py's
# own explicit commit()/rollback() calls (matching how main.py's lifespan
# actually drives it) -- a raw connection off test_engine instead, with
# this module doing its own setup/teardown, is truer to how the code
# actually runs.


def _seed_old_shape(conn) -> dict:
    """
    Builds the exact old-shape tables api/db/migrations/001_initial_schema.sql
    creates (confirmed live against a real freshly-initialized docker-compose
    stack, see issue #121), with a real FK-valid project and one seeded row
    per migrated table, so the test proves both "schema is now correct" and
    "pre-existing data survived the migration" -- not just the former.
    """
    conn.execute(text("DROP TABLE IF EXISTS conflict_log CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS sync_history CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS change_log CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS schema_migrations CASCADE"))

    project_id = str(uuid.uuid4())
    conn.execute(
        text(
            "INSERT INTO projects (id, name, user_id) VALUES "
            "(:id, 'pg-migration-test', '00000000-0000-0000-0000-000000000001') "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"id": project_id},
    )

    conn.execute(text(
        "CREATE TABLE change_log ("
        "    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,"
        "    entity_type VARCHAR(50) NOT NULL,"
        "    entity_id UUID NOT NULL,"
        "    operation VARCHAR(10) NOT NULL,"
        "    data JSONB,"
        "    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),"
        "    synced BOOLEAN DEFAULT FALSE,"
        "    CONSTRAINT change_log_operation_check CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE'))"
        ")"
    ))

    conn.execute(text(
        "CREATE TABLE sync_history ("
        "    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,"
        "    sync_direction VARCHAR(20) NOT NULL,"
        "    sync_mode VARCHAR(50) NOT NULL,"
        "    status VARCHAR(50) NOT NULL,"
        "    records_synced INTEGER DEFAULT 0,"
        "    errors JSONB,"
        "    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),"
        "    completed_at TIMESTAMP WITH TIME ZONE,"
        "    CONSTRAINT sync_history_direction_check CHECK (sync_direction IN ('push', 'pull')),"
        "    CONSTRAINT sync_history_status_check CHECK (status IN ('pending', 'running', 'completed', 'failed'))"
        ")"
    ))

    conn.execute(text(
        "CREATE TABLE conflict_log ("
        "    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,"
        "    entity_type VARCHAR(50) NOT NULL,"
        "    entity_id UUID NOT NULL,"
        "    local_value JSONB,"
        "    cloud_value JSONB,"
        "    local_timestamp TIMESTAMP WITH TIME ZONE,"
        "    cloud_timestamp TIMESTAMP WITH TIME ZONE,"
        "    resolution_strategy VARCHAR(50),"
        "    resolved_value JSONB,"
        "    resolved_at TIMESTAMP WITH TIME ZONE,"
        "    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"
        ")"
    ))

    conn.execute(
        text(
            "INSERT INTO sync_history "
            "(project_id, sync_direction, sync_mode, status, records_synced, started_at, completed_at) "
            "VALUES (:pid, 'push', 'full', 'completed', 42, NOW() - INTERVAL '1 hour', NOW())"
        ),
        {"pid": project_id},
    )
    # One row with a NULL resolved_at -- a conflict logged as detected but
    # not yet resolved under the old schema, where resolved_at was
    # nullable. Proves the NOT NULL backfill (COALESCE -> NOW()) works,
    # not just the happy path where every old column already has a value.
    conn.execute(
        text(
            "INSERT INTO conflict_log "
            "(project_id, entity_type, entity_id, local_value, cloud_value, resolution_strategy, resolved_value, resolved_at) "
            "VALUES (:pid, 'vector', gen_random_uuid(), '{\"a\": 1}'::jsonb, '{\"a\": 2}'::jsonb, 'local_wins', '{\"a\": 1}'::jsonb, NULL)"
        ),
        {"pid": project_id},
    )
    conn.commit()
    return {"project_id": project_id}


class TestPostgresSchemaMigration:
    """Refs #121."""

    def test_migrates_change_log_sync_history_conflict_log_from_old_shape(self, test_engine):
        with test_engine.connect() as conn:
            seeded = _seed_old_shape(conn)

            apply_pending_migrations(conn)

            # change_log: synced_at was added, nothing else changed.
            cols = {
                row[0] for row in conn.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'change_log'"
                )).fetchall()
            }
            assert "synced_at" in cols

            # sync_history: new shape, old row carried forward.
            row = conn.execute(
                text(
                    "SELECT direction, mode, status, records_synced "
                    "FROM sync_history WHERE project_id = :pid"
                ),
                {"pid": seeded["project_id"]},
            ).first()
            assert row is not None, "seeded sync_history row did not survive migration"
            assert row[0] == "push"
            assert row[1] == "full"
            assert row[2] == "completed"
            assert row[3] == {"total": 42}

            # conflict_log: new shape, old row carried forward, NULL
            # resolved_at backfilled rather than violating NOT NULL.
            row = conn.execute(
                text(
                    "SELECT local_version, cloud_version, resolution_strategy, "
                    "chosen_version, resolved_at FROM conflict_log WHERE project_id = :pid"
                ),
                {"pid": seeded["project_id"]},
            ).first()
            assert row is not None, "seeded conflict_log row did not survive migration"
            assert row[0] == {"a": 1}
            assert row[1] == {"a": 2}
            assert row[2] == "local_wins"
            assert row[3] == {"a": 1}
            assert row[4] is not None  # backfilled, not left NULL

    def test_migration_is_safe_to_run_twice(self, test_engine):
        """A database already on the new shape must no-op, not error."""
        with test_engine.connect() as conn:
            _seed_old_shape(conn)
            apply_pending_migrations(conn)
            # Second call against an already-migrated database: every
            # migration function's own shape check should no-op, and
            # the schema_migrations tracking table should short-circuit
            # it regardless.
            apply_pending_migrations(conn)

            applied = {
                row[0]
                for row in conn.execute(text("SELECT id FROM schema_migrations")).fetchall()
            }
            assert "121_change_log_synced_at" in applied
            assert "121_sync_history_column_rename" in applied
            assert "121_conflict_log_column_rename" in applied

    def test_fresh_database_already_on_new_shape_is_a_no_op(self, test_engine):
        """
        A database created from the current (fixed) schema.sql already has
        the new shape -- migrations must detect that and do nothing, not
        assume old-shape tables always exist.
        """
        with test_engine.connect() as conn:
            # No seeding: whatever schema.sql / init.sh already produced in
            # the test database is the baseline.
            apply_pending_migrations(conn)  # must not raise
