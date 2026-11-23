"""
Lite-mode SQLite schema migrations.

Refs #113: lite/services/database_service_lite.py's _init_schema() only
ever ran `CREATE TABLE IF NOT EXISTS ...` from schema_lite.sql -- a no-op
against a table that already exists under an older column layout. Every
past change to schema_lite.sql (e.g. #73/#79's sync_history/conflict_log
column renames) silently left any pre-existing database on the old shape
forever, surfacing later as an unhelpful 503 ("Database service is
temporarily unavailable") the first time a request actually touched the
mismatched table -- the real cause (sqlite3.OperationalError: no such
column: ...) was logged but never shown to the user or fixed automatically.

This module is the migration runner going forward: each schema change that
needs more than "CREATE TABLE IF NOT EXISTS" (anything a brand new
database wouldn't need, because it never had the old shape to begin with)
gets its own migration function here, registered in MIGRATIONS in the
order it must run. apply_pending_migrations() tracks which ones have
already run in a dedicated schema_migrations table and only runs new ones,
so it's safe to call on every startup.
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
        text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table_name},
    ).first()
    return row is not None


def _column_names(conn: Connection, table_name: str) -> set:
    rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return {row[1] for row in rows}


def _migrate_sync_history_columns(conn: Connection) -> None:
    """
    Refs #73/#113: an earlier schema_lite.sql shape for sync_history
    (sync_direction/sync_mode/errors columns, no sync_id/direction/mode/
    error_message/error_stack/snapshot_id/bytes_transferred/updated_at)
    predates api/models/sync_history.py's ORM model. CREATE TABLE IF NOT
    EXISTS never fixes a table that already exists under that old shape,
    so every pre-existing database kept it forever -- every ORM query
    against sync_history failed with "no such column: sync_history.sync_id"
    (confirmed live against a real, organically-aged database).

    SQLite's ALTER TABLE can't rename/retype columns the way this needs
    (sync_direction -> direction, sync_mode -> mode, etc. -- not just new
    columns), so this renames the old table aside, lets the normal
    CREATE TABLE IF NOT EXISTS in schema_lite.sql create a fresh one in the
    new shape, then copies forward whatever data maps cleanly. sync_id is
    NOT NULL UNIQUE in the new schema with no equivalent in the old one, so
    a synthetic value is generated per row rather than leaving it null.
    """
    if not _table_exists(conn, "sync_history"):
        return

    columns = _column_names(conn, "sync_history")
    if "sync_id" in columns:
        # Already the new shape (either a fresh database, or this
        # migration already ran) -- nothing to do.
        return

    logger.info("Migrating sync_history to the current schema (Refs #73/#113)")

    conn.execute(text("ALTER TABLE sync_history RENAME TO sync_history_pre_migration_113"))
    conn.execute(text(_SYNC_HISTORY_CREATE))

    old_columns = _column_names(conn, "sync_history_pre_migration_113")
    # Only copy columns that exist in the old table under their old names;
    # anything else (direction/mode/error_message/error_stack/snapshot_id/
    # bytes_transferred/updated_at) has no old-schema equivalent and is
    # left at its new-schema default for migrated rows.
    # sync_id is typed as a real UUID column on the ORM side (api/models/
    # sync_history.py's Column(UUID(as_uuid=True), ...)), not a free-form
    # string -- a synthetic value here must be UUID4-shaped (8-4-4-4-12 hex
    # groups) or SQLAlchemy raises ValueError("badly formed hexadecimal
    # UUID string") the first time this row is read back through the ORM.
    _SYNTHETIC_SYNC_ID = (
        "lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || "
        "substr(lower(hex(randomblob(2))), 2) || '-' || "
        "substr('89ab', 1 + (abs(random()) % 4), 1) || substr(lower(hex(randomblob(2))), 2) || '-' || "
        "lower(hex(randomblob(6)))"
    )
    select_parts = [f"({_SYNTHETIC_SYNC_ID}) AS sync_id", "id", "project_id"]
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
        select_parts.append("started_at")
        insert_cols.append("started_at")
    if "completed_at" in old_columns:
        select_parts.append("completed_at")
        insert_cols.append("completed_at")
    if "records_synced" in old_columns:
        select_parts.append("records_synced")
        insert_cols.append("records_synced")

    conn.execute(text(
        f"INSERT INTO sync_history ({', '.join(insert_cols)}) "
        f"SELECT {', '.join(select_parts)} FROM sync_history_pre_migration_113"
    ))
    conn.execute(text("DROP TABLE sync_history_pre_migration_113"))


def _migrate_conflict_log_columns(conn: Connection) -> None:
    """
    Refs #79/#113: same situation as sync_history above, for conflict_log
    -- an earlier shape (local_value/cloud_value/local_timestamp/
    cloud_timestamp/resolved_value, no local_version/cloud_version/
    chosen_version/detected_at/conflict_metadata/notes) predates
    api/models/conflict_log.py's ORM model, confirmed live as the exact
    cause of "no such column: conflict_log.local_version" on a real,
    pre-existing database.
    """
    if not _table_exists(conn, "conflict_log"):
        return

    columns = _column_names(conn, "conflict_log")
    if "local_version" in columns:
        return

    logger.info("Migrating conflict_log to the current schema (Refs #79/#113)")

    conn.execute(text("ALTER TABLE conflict_log RENAME TO conflict_log_pre_migration_113"))
    conn.execute(text(_CONFLICT_LOG_CREATE))

    old_columns = _column_names(conn, "conflict_log_pre_migration_113")
    select_parts = ["id", "project_id", "entity_type", "entity_id"]
    insert_cols = ["id", "project_id", "entity_type", "entity_id"]
    if "local_value" in old_columns:
        select_parts.append("local_value")
        insert_cols.append("local_version")
    if "cloud_value" in old_columns:
        select_parts.append("cloud_value")
        insert_cols.append("cloud_version")
    if "resolution_strategy" in old_columns:
        select_parts.append("resolution_strategy")
        insert_cols.append("resolution_strategy")
    if "resolved_value" in old_columns:
        select_parts.append("resolved_value")
        insert_cols.append("chosen_version")
    if "resolved_at" in old_columns:
        select_parts.append("resolved_at")
        insert_cols.append("resolved_at")

    # local_version/cloud_version/resolution_strategy/chosen_version are
    # NOT NULL in the new schema -- skip any old row missing a value this
    # migration can't backfill rather than violate the constraint.
    required = {"local_version", "cloud_version", "resolution_strategy", "chosen_version"}
    if required.issubset(set(insert_cols)):
        conn.execute(text(
            f"INSERT INTO conflict_log ({', '.join(insert_cols)}) "
            f"SELECT {', '.join(select_parts)} FROM conflict_log_pre_migration_113"
        ))
    else:
        logger.warning(
            "conflict_log_pre_migration_113 is missing a column this migration "
            "needs to backfill a required field -- old conflict rows were not "
            "carried forward, but the table itself is now on the current schema."
        )

    conn.execute(text("DROP TABLE conflict_log_pre_migration_113"))


# Mirrors the CREATE TABLE statements in schema_lite.sql exactly -- kept
# here instead of re-parsing the .sql file so each migration is a single,
# self-contained, independently reviewable unit.
_SYNC_HISTORY_CREATE = """
CREATE TABLE sync_history (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    sync_id TEXT NOT NULL UNIQUE,
    direction TEXT NOT NULL CHECK(direction IN ('push', 'pull', 'bidirectional')),
    mode TEXT NOT NULL CHECK(mode IN ('full', 'incremental', 'selective')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'completed', 'failed', 'rolled_back')),
    started_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    completed_at TEXT,
    records_synced TEXT DEFAULT '{}',
    bytes_transferred INTEGER DEFAULT 0,
    error_message TEXT,
    error_stack TEXT,
    snapshot_id TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
)
"""

_CONFLICT_LOG_CREATE = """
CREATE TABLE conflict_log (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    local_version TEXT NOT NULL,
    cloud_version TEXT NOT NULL,
    resolution_strategy TEXT NOT NULL,
    chosen_version TEXT NOT NULL,
    detected_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    resolved_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    conflict_metadata TEXT DEFAULT '{}',
    notes TEXT
)
"""


# Ordered list of (migration_id, function) -- migration_id must never
# change once released (it's the tracking key in schema_migrations), and
# new migrations are always appended, never inserted earlier in the list.
MIGRATIONS: List[Migration] = [
    ("113_sync_history_column_rename", _migrate_sync_history_columns),
    ("113_conflict_log_column_rename", _migrate_conflict_log_columns),
]


def apply_pending_migrations(conn: Connection) -> None:
    """
    Run every migration in MIGRATIONS that hasn't already been applied to
    this database, tracked by id in a dedicated schema_migrations table.
    Safe to call on every startup -- a fresh database has nothing to
    migrate (each migration function checks the actual column shape and
    no-ops if it's already current, in addition to the applied-migrations
    tracking table short-circuiting it), and an already-migrated database
    skips straight past.
    """
    conn.execute(text(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "    id TEXT PRIMARY KEY,"
        "    applied_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))"
        ")"
    ))

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
                "Schema migration '%s' failed -- the database may be left "
                "on an inconsistent schema until this is fixed. See the "
                "traceback above for the real cause.",
                migration_id,
            )
            raise
