"""
Full-mode (Postgres) schema migrations.

Refs #121: `api/db/init.sh` runs `001_initial_schema.sql` directly, and
Postgres's own `docker-entrypoint-initdb.d` convention then auto-runs every
other `.sh`/`.sql` file in that directory alphabetically too -- including
`schema.sql`, mounted alongside it. `schema.sql` creates `projects` with
`CREATE TABLE IF NOT EXISTS` (a no-op, since `init.sh` already created it),
but its very next statement, `CREATE INDEX idx_projects_user_id ...` (no
`IF NOT EXISTS`), then hard-fails on the duplicate index -- aborting
`schema.sql` entirely at that point. Every statement after it, including
`change_log`'s `synced_at` column and `sync_history`/`conflict_log`'s
correct (current ORM-model-matching) shapes, never actually runs against a
real database. `api/db/migrations/002`-`006` were written to fix exactly
this, but nothing ever executes them either -- `init.sh` only runs `001`,
and they're not `.sql` files directly in `docker-entrypoint-initdb.d`
(they're one level down, in `migrations/`, which Postgres's entrypoint
does not recurse into).

Net effect: every full-mode database ends up with `change_log` missing
`synced_at`, and `sync_history`/`conflict_log` on an old column shape that
predates their ORM models -- surfacing as 500/503s the first time a
request actually touches `/sync/status`, `/sync/history`, or
`/sync/conflicts/` (`psycopg2.errors.UndefinedColumn`), confirmed live
against a real, freshly-initialized `docker compose up -d` stack.

This module is the migration runner going forward, mirroring
`lite/db/migrations.py`'s pattern exactly: each schema fix needed beyond
what a correctly-idempotent `schema.sql` would give a brand-new database
gets its own migration function here, registered in MIGRATIONS in the
order it must run. `apply_pending_migrations()` tracks which ones have
already run in a dedicated `schema_migrations` table and only runs new
ones, so it's safe to call on every `zerodb-api` startup -- including
against a database that already has the correct shape (each migration
function checks the actual column shape and no-ops if already current, on
top of the tracking table short-circuiting it).
"""
from __future__ import annotations

import logging
from typing import Callable, List, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)

Migration = Tuple[str, Callable[[Connection], None]]


def _table_exists(conn: Connection, table_name: str) -> bool:
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :name"
        ),
        {"name": table_name},
    ).first()
    return row is not None


def _column_names(conn: Connection, table_name: str) -> set:
    rows = conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :name"
        ),
        {"name": table_name},
    ).fetchall()
    return {row[0] for row in rows}


def _migrate_change_log_synced_at(conn: Connection) -> None:
    """
    Refs #121: `change_log`'s ORM model (api/models/change_log.py) has
    always included `synced_at`, and the current `schema.sql` does too --
    but `001_initial_schema.sql` (the only thing `init.sh` actually runs)
    predates it, and `schema.sql` never reaches its own `change_log`
    definition (aborts earlier, see module docstring). A simple `ADD
    COLUMN IF NOT EXISTS` is correct and sufficient here: unlike
    sync_history/conflict_log below, this is a pure addition with no
    renamed/retyped columns to reconcile.
    """
    if not _table_exists(conn, "change_log"):
        return
    if "synced_at" in _column_names(conn, "change_log"):
        return

    logger.info("Migrating change_log: adding synced_at column (Refs #121)")
    conn.execute(text(
        "ALTER TABLE change_log ADD COLUMN IF NOT EXISTS "
        "synced_at TIMESTAMP WITH TIME ZONE DEFAULT NULL"
    ))


def _migrate_sync_history_columns(conn: Connection) -> None:
    """
    Refs #121: `001_initial_schema.sql`'s `sync_history` shape
    (sync_direction/sync_mode/records_synced INTEGER, no sync_id/direction/
    mode/error_message/error_stack/snapshot_id/bytes_transferred/
    updated_at) predates `api/models/sync_history.py`'s ORM model --
    confirmed live as the exact cause of `psycopg2.errors.UndefinedColumn:
    column sync_history.sync_id does not exist` type failures against a
    real, freshly-initialized database (schema.sql's correct definition
    for this table never actually runs; see module docstring).

    Postgres's ALTER TABLE can retype/rename individual columns, but this
    needs several at once plus a type change on records_synced (INTEGER ->
    JSONB) and a NOT NULL UNIQUE addition (sync_id) with no old-schema
    equivalent -- simplest and most auditable as rename-aside, recreate,
    copy-forward, matching lite/db/migrations.py's approach for the exact
    same problem in SQLite.
    """
    if not _table_exists(conn, "sync_history"):
        return

    columns = _column_names(conn, "sync_history")
    if "sync_id" in columns:
        # Already the new shape (either a fresh database -- this needs the
        # schema.sql idempotency fix too -- or this migration already ran).
        return

    logger.info("Migrating sync_history to the current schema (Refs #121)")

    conn.execute(text("ALTER TABLE sync_history RENAME TO sync_history_pre_migration_121"))
    conn.execute(text(_SYNC_HISTORY_CREATE))

    old_columns = _column_names(conn, "sync_history_pre_migration_121")
    # sync_id is NOT NULL UNIQUE in the new schema with no old-schema
    # equivalent -- generate one per row via gen_random_uuid() rather than
    # leaving it null (would violate NOT NULL).
    select_parts = ["gen_random_uuid() AS sync_id", "id", "project_id"]
    insert_cols = ["sync_id", "id", "project_id"]
    if "sync_direction" in old_columns:
        select_parts.append("sync_direction")
        insert_cols.append("direction")
    if "sync_mode" in old_columns:
        select_parts.append("sync_mode")
        insert_cols.append("mode")
    if "status" in old_columns:
        select_parts.append("status")
        insert_cols.append("status")
    if "started_at" in old_columns:
        # NOT NULL in the new schema, nullable (DEFAULT NOW() but no NOT
        # NULL) in the old one -- a straight copy can carry an old NULL
        # into a column that now forbids it.
        select_parts.append("COALESCE(started_at, NOW())")
        insert_cols.append("started_at")
    if "completed_at" in old_columns:
        select_parts.append("completed_at")
        insert_cols.append("completed_at")
    if "records_synced" in old_columns:
        # Old column is INTEGER (a count), new column is JSONB (per-entity
        # breakdown) -- not a compatible value, so wrap it rather than cast.
        select_parts.append(
            "jsonb_build_object('total', records_synced) AS records_synced"
        )
        insert_cols.append("records_synced")

    conn.execute(text(
        f"INSERT INTO sync_history ({', '.join(insert_cols)}) "
        f"SELECT {', '.join(select_parts)} FROM sync_history_pre_migration_121"
    ))
    conn.execute(text("DROP TABLE sync_history_pre_migration_121"))


def _migrate_conflict_log_columns(conn: Connection) -> None:
    """
    Refs #121: same situation as sync_history above, for conflict_log --
    `001_initial_schema.sql`'s shape (local_value/cloud_value/
    resolution_strategy/resolved_value/resolved_at, no local_version/
    cloud_version/chosen_version/detected_at/conflict_metadata/notes)
    predates `api/models/conflict_log.py`'s ORM model, confirmed live as
    the exact cause of "column conflict_log.local_version does not exist".
    """
    if not _table_exists(conn, "conflict_log"):
        return

    columns = _column_names(conn, "conflict_log")
    if "local_version" in columns:
        return

    logger.info("Migrating conflict_log to the current schema (Refs #121)")

    conn.execute(text("ALTER TABLE conflict_log RENAME TO conflict_log_pre_migration_121"))
    conn.execute(text(_CONFLICT_LOG_CREATE))

    old_columns = _column_names(conn, "conflict_log_pre_migration_121")
    select_parts = ["id", "project_id", "entity_type", "entity_id"]
    insert_cols = ["id", "project_id", "entity_type", "entity_id"]
    # local_version/cloud_version/resolution_strategy/chosen_version are
    # NOT NULL in the new schema but nullable in the old one -- each old
    # row's value for these, not just whether the old column exists at
    # all, decides whether that row can be carried forward (a WHERE
    # clause below excludes any row missing one, rather than violating
    # the constraint on INSERT or dropping ALL rows over one gap).
    required_old_to_new = {
        "local_value": "local_version",
        "cloud_value": "cloud_version",
        "resolution_strategy": "resolution_strategy",
        "resolved_value": "chosen_version",
    }
    where_parts = []
    for old_name, new_name in required_old_to_new.items():
        if old_name in old_columns:
            select_parts.append(f"{old_name} AS {new_name}")
            insert_cols.append(new_name)
            where_parts.append(f"{old_name} IS NOT NULL")
        else:
            # Old table has no equivalent for this required column at
            # all -- no row from it can ever satisfy the new NOT NULL
            # constraint, so there's nothing to copy.
            where_parts = None
            break
    if "resolved_at" in old_columns:
        # NOT NULL in the new schema, nullable in the old one (a conflict
        # could be logged as detected but not yet resolved) -- a straight
        # copy can carry an old NULL into a column that now forbids it.
        select_parts.append("COALESCE(resolved_at, NOW())")
        insert_cols.append("resolved_at")

    if where_parts is not None:
        where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
        result = conn.execute(text(
            f"INSERT INTO conflict_log ({', '.join(insert_cols)}) "
            f"SELECT {', '.join(select_parts)} FROM conflict_log_pre_migration_121"
            f"{where_clause}"
        ))
        total = conn.execute(
            text("SELECT COUNT(*) FROM conflict_log_pre_migration_121")
        ).scalar()
        if result.rowcount < total:
            logger.warning(
                "conflict_log migration: carried forward %d of %d old rows "
                "-- the rest had a NULL in a field the new schema requires "
                "and were left behind.",
                result.rowcount, total,
            )
    else:
        logger.warning(
            "conflict_log_pre_migration_121 is missing a column this "
            "migration needs to backfill a required field -- old conflict "
            "rows were not carried forward, but the table itself is now on "
            "the current schema."
        )

    conn.execute(text("DROP TABLE conflict_log_pre_migration_121"))


def _migrate_create_sync_plans(conn: Connection) -> None:
    """
    Refs #127: api/models/sync_plan.py's SyncPlan ORM model has existed
    with no backing table in any schema file or migration -- confirmed
    live as the cause of every /sync/plan and /sync/execute call failing
    with "relation sync_plans does not exist" (silently swallowed on the
    preview endpoint, a hard 500 on execute). No old shape to reconcile
    here, unlike sync_history/conflict_log above -- this table simply
    never existed, so a plain idempotent CREATE is sufficient.
    """
    if _table_exists(conn, "sync_plans"):
        return

    logger.info("Creating missing sync_plans table (Refs #127)")
    conn.execute(text(_SYNC_PLANS_CREATE))


# Mirrors api/db/migrations/004_sync_history.sql and 004_conflict_log.sql
# exactly -- kept here instead of reading those files at runtime so each
# migration is a single, self-contained, independently reviewable unit,
# matching lite/db/migrations.py's approach.
_SYNC_HISTORY_CREATE = """
CREATE TABLE sync_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    sync_id UUID NOT NULL UNIQUE,
    direction VARCHAR(20) NOT NULL CHECK (direction IN ('push', 'pull', 'bidirectional')),
    mode VARCHAR(20) NOT NULL CHECK (mode IN ('full', 'incremental', 'selective')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'rolled_back')),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    records_synced JSONB NOT NULL DEFAULT '{}'::jsonb,
    bytes_transferred BIGINT DEFAULT 0,
    error_message TEXT,
    error_stack TEXT,
    snapshot_id UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
)
"""

_CONFLICT_LOG_CREATE = """
CREATE TABLE conflict_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(512) NOT NULL,
    local_version JSONB NOT NULL,
    cloud_version JSONB NOT NULL,
    resolution_strategy VARCHAR(50) NOT NULL,
    chosen_version JSONB NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    conflict_metadata JSONB DEFAULT '{}'::jsonb,
    notes TEXT
)
"""

# Mirrors api/models/sync_plan.py's SyncPlan ORM model exactly -- see
# _migrate_create_sync_plans() above (Refs #127).
_SYNC_PLANS_CREATE = """
CREATE TABLE sync_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL UNIQUE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    direction VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    steps JSONB NOT NULL,
    total_steps INTEGER NOT NULL DEFAULT 0,
    entity_counts JSONB NOT NULL,
    estimated_duration_seconds DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    estimated_data_size_bytes INTEGER NOT NULL DEFAULT 0,
    schema_changes JSONB NOT NULL,
    conflicts JSONB NOT NULL,
    warnings TEXT[] NOT NULL DEFAULT '{}',
    requires_approval BOOLEAN NOT NULL DEFAULT FALSE,
    can_rollback BOOLEAN NOT NULL DEFAULT TRUE,
    approved_by VARCHAR(255),
    approved_at TIMESTAMP WITHOUT TIME ZONE,
    executed_at TIMESTAMP WITHOUT TIME ZONE,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    sync_result_id UUID,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
    expires_at TIMESTAMP WITHOUT TIME ZONE
);
CREATE INDEX idx_sync_plans_plan_id ON sync_plans(plan_id);
CREATE INDEX idx_sync_plans_project_id ON sync_plans(project_id);
CREATE INDEX idx_sync_plans_status ON sync_plans(status);
CREATE INDEX idx_sync_plans_created_at ON sync_plans(created_at);
CREATE INDEX idx_sync_plans_expires_at ON sync_plans(expires_at);
"""


# Ordered list of (migration_id, function) -- migration_id must never
# change once released (it's the tracking key in schema_migrations), and
# new migrations are always appended, never inserted earlier in the list.
MIGRATIONS: List[Migration] = [
    ("121_change_log_synced_at", _migrate_change_log_synced_at),
    ("121_sync_history_column_rename", _migrate_sync_history_columns),
    ("121_conflict_log_column_rename", _migrate_conflict_log_columns),
    ("127_create_sync_plans", _migrate_create_sync_plans),
]


def apply_pending_migrations(conn: Connection) -> None:
    """
    Run every migration in MIGRATIONS that hasn't already been applied to
    this database, tracked by id in a dedicated schema_migrations table.
    Safe to call on every zerodb-api startup -- a correctly-shaped
    database has nothing to migrate (each migration function checks the
    actual column shape and no-ops if it's already current, in addition to
    the applied-migrations tracking table short-circuiting it), and an
    already-migrated database skips straight past.
    """
    conn.execute(text(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "    id TEXT PRIMARY KEY,"
        "    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"
        ")"
    ))
    conn.commit()

    applied = {
        row[0]
        for row in conn.execute(text("SELECT id FROM schema_migrations")).fetchall()
    }

    for migration_id, migration_fn in MIGRATIONS:
        if migration_id in applied:
            continue
        try:
            migration_fn(conn)
            conn.execute(
                text("INSERT INTO schema_migrations (id) VALUES (:id)"),
                {"id": migration_id},
            )
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception(
                "Postgres schema migration '%s' failed -- the database may "
                "be left on an inconsistent schema until this is fixed. "
                "See the traceback above for the real cause.",
                migration_id,
            )
            raise
