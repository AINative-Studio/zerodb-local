"""
ZeroDB Local - Backend Selector Configuration

Reads ZERODB_BACKEND env var to determine whether to run in "lite" or "full" mode.
- lite: SQLite + FAISS + filesystem (zero infrastructure)
- full: PostgreSQL + Qdrant + MinIO + RedPanda (production stack)

Auto-detection: if DATABASE_URL starts with "postgresql://", defaults to "full";
otherwise defaults to "lite".
"""
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Data directories
# ---------------------------------------------------------------------------
DATA_DIR: Path = Path(os.getenv("ZERODB_DATA_DIR", "~/.zerodb/data/")).expanduser()
MODELS_DIR: Path = Path(os.getenv("ZERODB_MODELS_DIR", "~/.zerodb/models/")).expanduser()

# Ensure base directories exist on import
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------
_VALID_BACKENDS = ("lite", "full")


def _detect_backend() -> str:
    """
    Determine the active backend.

    Priority:
      1. Explicit ZERODB_BACKEND env var ("lite" or "full")
      2. Auto-detect from DATABASE_URL prefix
      3. Default to "lite"
    """
    explicit = os.getenv("ZERODB_BACKEND", "").strip().lower()
    if explicit in _VALID_BACKENDS:
        return explicit

    database_url = os.getenv("DATABASE_URL", "")
    if database_url.startswith("postgresql://"):
        return "full"

    return "lite"


ZERODB_BACKEND: str = _detect_backend()


def is_lite_mode() -> bool:
    """Return True when running in lite (zero-infrastructure) mode."""
    return ZERODB_BACKEND == "lite"


def is_full_mode() -> bool:
    """Return True when running in full (production-stack) mode."""
    return ZERODB_BACKEND == "full"


def get_data_path(subpath: str, is_dir: bool = True) -> Path:
    """
    Resolve a path under DATA_DIR, creating intermediate directories on demand.

    Args:
        subpath: Relative path under the data directory (e.g. "collections/default" or "zerodb.db").
        is_dir: If True, create the path as a directory. If False, create only parent dirs (for files).

    Returns:
        Absolute Path with all parent directories created.
    """
    target = DATA_DIR / subpath
    if is_dir:
        target.mkdir(parents=True, exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
    return target
