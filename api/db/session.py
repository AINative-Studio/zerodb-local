"""
Database Session Module
Re-exports database utilities for backward compatibility

`get_db` and `Base` are cheap to import eagerly. `engine`/`SessionLocal` are
re-exported lazily via module `__getattr__` (PEP 562) so merely importing
this module (as `main.py`'s router chain does) doesn't force construction of
the underlying SQLAlchemy engine -- which, in full mode, requires psycopg2
to be installed. Refs #50.
"""
from database import get_db, Base
import database as _database

__all__ = ["get_db", "engine", "SessionLocal", "Base"]  # noqa: F822 (engine/SessionLocal served by __getattr__ below, PEP 562)


def __getattr__(name: str):
    if name in ("engine", "SessionLocal"):
        return getattr(_database, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
