"""
Shared SQLAlchemy column types for cross-dialect (PostgreSQL + SQLite)
model compatibility.
"""
import uuid as _uuid_module

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator


class LiteCompatibleDateTime(TypeDecorator):
    """
    A DateTime column that also round-trips lite mode's SQLite rows.

    lite/db/schema_lite.sql's column defaults and lite/sql_compat.py's
    now_iso() both write timestamps as TEXT in the form
    "%Y-%m-%dT%H:%M:%f" + a trailing "Z" (deliberately, so rows written by
    Python code and rows written by a SQL-level DEFAULT sort and compare
    identically -- see sql_compat.py). PostgreSQL never sees this: it has a
    native timestamp type, so writes there go through datetime objects, not
    this string format, and SQLAlchemy's postgres dialect decodes its own
    wire format directly.

    On SQLite, SQLAlchemy decodes a TIMESTAMP/DateTime column by calling
    datetime.fromisoformat() on the stored TEXT value (see
    sqlalchemy.cyextension.processors.str_to_datetime, or its pure-Python
    equivalent). datetime.fromisoformat() only accepts a trailing "Z" from
    Python 3.11 onward (https://docs.python.org/3/whatsnew/3.11.html); on
    3.10 and earlier it raises "Invalid isoformat string" for any value
    carrying one, which previously surfaced as a 400 on every endpoint that
    serializes one of these columns in lite mode (Refs #103). Stripping the
    trailing "Z" before SQLAlchemy's own fromisoformat() call makes this
    column decode correctly on every supported Python version without
    touching the write-side convention or schema defaults.
    """

    impl = DateTime
    cache_ok = True

    def result_processor(self, dialect, coltype):
        # TypeDecorator.process_result_value runs *after* the impl's own
        # result_processor -- too late here, since DateTime's SQLite
        # processor (sqlalchemy.cyextension.processors.str_to_datetime, or
        # its pure-Python equivalent) is what raises on the trailing "Z"
        # before our hook would ever see the value. Strip it beforehand by
        # wrapping the raw DBAPI value instead.
        impl_processor = super().result_processor(dialect, coltype)

        def process(value):
            if isinstance(value, str) and value.endswith("Z"):
                value = value[:-1]
            if impl_processor is not None:
                return impl_processor(value)
            return value

        return process


class LiteCompatibleUUID(TypeDecorator):
    """
    A UUID foreign-key column that also filters correctly against lite
    mode's SQLite rows.

    Refs #113: sync_history.project_id/conflict_log.project_id both
    reference projects.id (REFERENCES projects(id), enforced by a real
    FOREIGN KEY constraint in lite/db/schema_lite.sql). projects.id itself
    is written as a dashed UUID string in lite mode (lite/sql_compat.py's
    new_id(), str(uuid4())) -- a plain TEXT column with no ORM UUID
    coercion, so that FK constraint requires project_id to match it
    exactly, dashes included.

    sqlalchemy.dialects.postgresql.UUID(as_uuid=True) (the type these
    columns used, matching the ORM model full mode shares with Postgres)
    binds a Python UUID object into a SQLite query's WHERE clause as the
    *hex* form (no dashes) -- confirmed directly via its own
    bind_processor(). So `WHERE project_id = :project_id` (built from a
    UUID-typed project_id path/query parameter, e.g. every route in
    api/routers/sync_history.py and conflict_resolution.py) silently
    matched zero rows against a dashed-stored value, even though the same
    value reads back correctly outside a filter (PG_UUID's own
    result_processor already accepts both forms) and the row genuinely
    exists. Confirmed directly: a real lite-mode database with a
    pre-existing sync_history row, migrated to the current schema, served
    0 results from GET /sync/history for the project that row actually
    belongs to.

    Only the bind side needs fixing. TypeDecorator.process_bind_param's
    return value is NOT the final DBAPI value -- it's fed through the
    impl's own bind_processor afterward (the mirror image of
    LiteCompatibleDateTime's result_processor override above, and for the
    same reason: the hook that looks like "where you customize this" runs
    too early/late to actually own the final value). Overriding
    bind_processor directly, dialect-gated, replaces PG_UUID's hex-only
    SQLite encoding with Python's own str() (dashed) on SQLite only;
    PostgreSQL keeps PG_UUID's own native behavior untouched.
    """

    impl = PG_UUID(as_uuid=True)
    cache_ok = True

    def bind_processor(self, dialect):
        if dialect.name != "sqlite":
            return self.impl.bind_processor(dialect)

        def process(value):
            if value is None:
                return None
            if isinstance(value, _uuid_module.UUID):
                return str(value)
            return value

        return process
