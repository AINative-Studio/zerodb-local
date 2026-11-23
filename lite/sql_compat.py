"""
SQL Dialect Compatibility Helpers

Refs #47: api/services/{tables,files,events,memory,vector}_service.py hardcode
raw SQL for PostgreSQL's jsonb type, the @> containment operator, the ||
concatenation operator, and NOW() -- none of which exist in SQLite. These
helpers let each service branch on is_lite_mode() (or an explicit dialect
name) while keeping a single code path per operation, instead of duplicating
every query.

Design notes:
- jsonb columns are stored as plain TEXT in lite/db/schema_lite.sql, so a
  "CAST(x AS jsonb)" in Postgres becomes a plain bind param in SQLite -- the
  value is already a JSON string from json.dumps(), so no cast is needed.
- SQLite's json_extract() replaces Postgres's @> containment operator for the
  equality-filter case these services actually use (filter_data is always a
  flat {field: value} dict of exact-match filters, never used for deep/partial
  containment). This is not a general @> -> json_extract rewrite -- it only
  covers the flat equality-filter shape these 5 services pass today.
- SQLite has no || jsonb concatenation operator; updates merge the existing
  row's JSON with the new fields in Python and write the merged JSON back.
- SQLite has no NOW(); the current UTC timestamp is computed in Python and
  bound as a parameter instead of embedded in the SQL string.
- SQLite has no native vector type; embeddings are stored as a JSON-encoded
  list of floats in a TEXT column (see memory_service.py / vector_service.py).

Refs #63: in full mode, every INSERT/UPDATE/DELETE on vectors/table_rows/
memory/events/files is logged into `change_log` automatically by PL/pgSQL
triggers (api/db/migrations/001_initial_schema.sql, 003_change_detection.sql)
so sync_orchestrator.py's CDC-based sync-plan query sees it for free. SQLite
has no equivalent trigger support, so these 5 services must log the same
change_log row explicitly in lite mode -- log_cdc_change() below does that,
matching the triggers' exact entity_type ('vector', 'table_row', 'memory',
'event', 'file' -- singular) and operation ('INSERT'/'UPDATE'/'DELETE') string
contract that api/services/cdc_service.py's get_unsynced_changes() queries
against, so a lite-mode write is indistinguishable from a full-mode one to
the sync orchestrator.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from lite.config import is_lite_mode


def new_id() -> str:
    """
    Generate a new primary-key id for an INSERT.

    PostgreSQL's schema (api/db/schema.sql) declares every table's `id`
    column `UUID PRIMARY KEY DEFAULT gen_random_uuid()`, so an INSERT that
    omits `id` still gets one from the column default. SQLite's schema
    (lite/db/schema_lite.sql) declares the same column `TEXT PRIMARY KEY`
    with no default -- an INSERT that omits it silently stores NULL rather
    than erroring, corrupting the row's id. Callers must generate and bind
    this explicitly for every INSERT in lite mode.
    """
    return str(uuid.uuid4())


def now_iso() -> str:
    """Current UTC timestamp in the same string shape lite/db/schema_lite.sql
    column defaults use (so rows written by Python code and rows written by
    a SQL-level DEFAULT sort and compare identically)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def to_isoformat(value: Any) -> Optional[str]:
    """
    Normalize a timestamp column value to an ISO-8601 string.

    PostgreSQL (via psycopg2) returns timestamp columns as datetime objects,
    so the existing code calls .isoformat() on them. SQLite has no native
    datetime type -- it returns the TEXT value that was stored, which is
    already an ISO-8601 string. Handle both without assuming either.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


def parse_json_column(value: Any) -> Any:
    """
    Parse a JSON column value returned by the driver.

    PostgreSQL's psycopg2 driver deserializes jsonb columns to dict/list
    automatically. SQLite has no jsonb type -- these columns are TEXT in
    lite/db/schema_lite.sql, so the driver returns the raw JSON string and
    it must be parsed explicitly.
    """
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


def dump_json_param(value: Any) -> str:
    """Serialize a value for a jsonb/TEXT column bind parameter."""
    if value is None:
        return "{}"
    return json.dumps(value)


def jsonb_cast_sql(expr: str, lite: Optional[bool] = None) -> str:
    """
    Return the SQL fragment to store a JSON bind parameter in a jsonb (full
    mode) or TEXT (lite mode) column.

    Postgres needs the explicit CAST(:x AS jsonb) so the driver's text
    parameter is coerced to jsonb; SQLite has no jsonb type, and the value
    is already a JSON-encoded string, so passing the bind parameter through
    unchanged is correct and avoids the "unrecognized token" that an
    unconditional CAST ... AS jsonb silently tolerates but a real jsonb-only
    operator (@>, ||) would not.
    """
    if lite is None:
        lite = is_lite_mode()
    return expr if lite else f"CAST({expr} AS jsonb)"


def now_sql(lite: Optional[bool] = None) -> str:
    """
    Return the SQL fragment for "current timestamp" usable directly inside a
    SET/VALUES clause (e.g. "updated_at = {now_sql()}").

    Postgres: NOW(). SQLite: no NOW() function, so a bind parameter must be
    supplied by the caller -- this returns the bind placeholder, and the
    caller must include `"now": now_iso()` in the params dict.
    """
    if lite is None:
        lite = is_lite_mode()
    return ":now" if lite else "NOW()"


def equality_filter_clause(
    filter_data: Optional[Dict[str, Any]],
    column: str = "data",
    lite: Optional[bool] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Build a SQL fragment + bind params for a flat equality filter against a
    JSON column, replacing PostgreSQL's `column @> CAST(:filter AS jsonb)`
    containment operator (which SQLite doesn't have).

    Only covers the shape these services actually use: filter_data is a flat
    {field: value} dict and a row matches when every field equals its value
    in the stored JSON -- not partial/nested containment.

    Returns ("" , {}) when filter_data is empty/None (no filtering).
    """
    if lite is None:
        lite = is_lite_mode()

    if not filter_data:
        return "", {}

    if not lite:
        return f" AND {column} @> CAST(:filter AS jsonb)", {
            "filter": json.dumps(filter_data)
        }

    clauses = []
    params: Dict[str, Any] = {}
    for i, (key, value) in enumerate(filter_data.items()):
        param_name = f"filter_{i}"
        clauses.append(f"json_extract({column}, '$.{key}') = :{param_name}")
        if isinstance(value, bool):
            params[param_name] = 1 if value else 0
        else:
            params[param_name] = value

    return " AND " + " AND ".join(clauses), params


def merge_json_text(existing: Any, update: Dict[str, Any]) -> str:
    """
    Merge `update` into an existing JSON column value and re-serialize it,
    replacing PostgreSQL's `column || CAST(:update AS jsonb)` concatenation
    operator (which SQLite doesn't have).
    """
    existing_data = parse_json_column(existing)
    if isinstance(existing_data, dict):
        merged = {**existing_data, **update}
    else:
        merged = update
    return json.dumps(merged)


def log_cdc_change(
    db: Session,
    project_id: Any,
    entity_type: str,
    entity_id: Any,
    operation: str,
    data: Any = None,
) -> None:
    """
    Record a change_log row for lite mode, mirroring what a PL/pgSQL CDC
    trigger does for free in full mode (see module docstring, Refs #63).

    Only call this when is_lite_mode() is True -- full mode must NOT call
    this, since its own triggers already log the same write; calling both
    would double-log every change.

    Args:
        db: The same SQLAlchemy Session the caller's write used (so the
            change_log row commits atomically with the write it describes).
        project_id: Owning project UUID (str or UUID).
        entity_type: Singular entity name matching the full-mode trigger
            contract: one of 'vector', 'table_row', 'memory', 'event', 'file'.
        entity_id: UUID of the row that changed (str or UUID).
        operation: One of 'INSERT', 'UPDATE', 'DELETE' (matches change_log's
            CHECK constraint in both schema_lite.sql and the Postgres schema).
        data: The entity payload at the time of the change (dict, or a
            pre-serialized JSON string); stored as-is if already a string.
    """
    if data is not None and not isinstance(data, str):
        data = json.dumps(data, default=str)

    db.execute(
        text(
            """
            INSERT INTO change_log (id, project_id, entity_type, entity_id,
                                     operation, data, timestamp, synced)
            VALUES (:id, :project_id, :entity_type, :entity_id,
                    :operation, :data, :timestamp, 0)
            """
        ),
        {
            "id": new_id(),
            "project_id": str(project_id),
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "operation": operation,
            "data": data,
            "timestamp": now_iso(),
        },
    )
