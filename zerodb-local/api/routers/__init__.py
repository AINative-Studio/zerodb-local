"""
API Routers Package
Exports all routers for easy import
"""
from .projects import router as projects_router
from .vectors import router as vectors_router
from .memory import router as memory_router
from .tables import router as tables_router
from .files import router as files_router
from .events import router as events_router

__all__ = [
    "projects_router",
    "vectors_router",
    "memory_router",
    "tables_router",
    "files_router",
    "events_router",
]
