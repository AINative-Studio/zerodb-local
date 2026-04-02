"""
Lightweight server factory for pip-installed usage.

When zerodb-local is installed via pip (without the full source tree),
this module provides a minimal FastAPI app that can be started with
`zerodb serve`.  When the full api/ directory is available it delegates
to the real application.
"""

import sys
from pathlib import Path

from fastapi import FastAPI


def create_app() -> FastAPI:
    """
    Create and return a FastAPI application.

    Attempts to import the full API app from the source tree first.
    Falls back to a minimal health-check app when running from a
    pip install.
    """
    source_api_dir = Path(__file__).resolve().parent.parent / "api"

    if source_api_dir.is_dir():
        sys.path.insert(0, str(source_api_dir))
        try:
            from main import app as full_app

            return full_app
        except ImportError:
            pass

    # Minimal fallback app
    from zerodb_local import __version__

    app = FastAPI(
        title="ZeroDB Local",
        description="ZeroDB Local API server",
        version=__version__,
    )

    @app.get("/health")
    async def health():
        return {"status": "healthy", "version": __version__}

    @app.get("/")
    async def root():
        return {
            "service": "ZeroDB Local",
            "version": __version__,
            "status": "operational",
        }

    return app
