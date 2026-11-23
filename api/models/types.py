"""
Shared SQLAlchemy column types for cross-dialect (PostgreSQL + SQLite)
model compatibility.
"""
from sqlalchemy import DateTime
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
