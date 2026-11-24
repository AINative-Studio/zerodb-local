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


class TestSyncPlansMigration:
    """
    Refs #127: api/models/sync_plan.py's SyncPlan ORM model has existed
    with no backing table anywhere -- every real /sync/plan and
    /sync/execute call failed with
    "relation sync_plans does not exist". These test only that the table
    and its shape now exist via the migration runner; actually inserting
    through the ORM is still blocked by the separate, systemic bug
    tracked as #129 (see test_sync_plan_persistence.py's skip reason) --
    this intentionally uses raw SQL, not the SyncPlan model, to stay
    within #127's actual scope.
    """

    def test_creates_sync_plans_table_with_expected_columns(self, test_engine):
        with test_engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS sync_plans CASCADE"))
            # Also clear the tracking row -- otherwise apply_pending_migrations()
            # correctly (by design) skips re-running a migration it already
            # recorded as applied in an earlier test in this same session-scoped
            # test_engine, even though this test just dropped its table.
            conn.execute(text(
                "DELETE FROM schema_migrations WHERE id = '127_create_sync_plans'"
            ))
            conn.commit()

            apply_pending_migrations(conn)

            cols = {
                row[0] for row in conn.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'sync_plans'"
                )).fetchall()
            }
            expected = {
                "id", "plan_id", "project_id", "direction", "status",
                "steps", "total_steps", "entity_counts",
                "estimated_duration_seconds", "estimated_data_size_bytes",
                "schema_changes", "conflicts", "warnings",
                "requires_approval", "can_rollback", "approved_by",
                "approved_at", "executed_at", "completed_at",
                "sync_result_id", "created_at", "expires_at",
            }
            assert expected.issubset(cols)

    def test_raw_insert_and_select_round_trips(self, test_engine):
        """
        Confirms the table itself (constraints, column types, FK to
        projects) is genuinely usable for real rows, independent of
        whether the ORM layer can write to it (#129).
        """
        with test_engine.connect() as conn:
            apply_pending_migrations(conn)

            project_id = conn.execute(text(
                "INSERT INTO projects (name, user_id) VALUES "
                "('sync-plans-migration-test', "
                "'00000000-0000-0000-0000-000000000001') RETURNING id"
            )).scalar()

            plan_id = conn.execute(text(
                "INSERT INTO sync_plans "
                "(plan_id, project_id, direction, steps, entity_counts, "
                "schema_changes, conflicts) "
                "VALUES (gen_random_uuid(), :project_id, 'push', "
                "'[]'::jsonb, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb) "
                "RETURNING plan_id"
            ), {"project_id": project_id}).scalar()
            conn.commit()

            row = conn.execute(
                text("SELECT status, requires_approval, can_rollback FROM sync_plans WHERE plan_id = :pid"),
                {"pid": plan_id},
            ).first()
            assert row is not None
            assert row[0] == "pending"  # default
            assert row[1] is False  # default
            assert row[2] is True  # default

    def test_warnings_column_holds_structured_objects(self, test_engine):
        """
        Refs #131: warnings is JSONB, not TEXT[] -- it must hold the
        structured {severity, message, category} shape
        schemas/sync_orchestrator.py's SyncWarning produces and
        dashboard/app/sync/page.tsx's `w.message` rendering expects, not
        a flat list of strings.
        """
        with test_engine.connect() as conn:
            apply_pending_migrations(conn)

            project_id = conn.execute(text(
                "INSERT INTO projects (name, user_id) VALUES "
                "('sync-plans-warnings-test', "
                "'00000000-0000-0000-0000-000000000001') RETURNING id"
            )).scalar()

            plan_id = conn.execute(text(
                "INSERT INTO sync_plans "
                "(plan_id, project_id, direction, steps, entity_counts, "
                "schema_changes, conflicts, warnings) "
                "VALUES (gen_random_uuid(), :project_id, 'push', "
                "'[]'::jsonb, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, "
                "'[{\"severity\": \"low\", \"message\": \"No entities to sync\", "
                "\"category\": \"data\"}]'::jsonb) "
                "RETURNING plan_id"
            ), {"project_id": project_id}).scalar()
            conn.commit()

            warnings = conn.execute(
                text("SELECT warnings FROM sync_plans WHERE plan_id = :pid"),
                {"pid": plan_id},
            ).scalar()
            assert warnings == [{"severity": "low", "message": "No entities to sync", "category": "data"}]

    def test_migration_is_idempotent(self, test_engine):
        with test_engine.connect() as conn:
            apply_pending_migrations(conn)
            apply_pending_migrations(conn)  # must not raise on a second run

            applied = {
                row[0]
                for row in conn.execute(text("SELECT id FROM schema_migrations")).fetchall()
            }
            assert "127_create_sync_plans" in applied
