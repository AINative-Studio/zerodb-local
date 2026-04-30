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
from .change_detection import router as change_detection_router
from .sync_state import router as sync_state_router
from .cloud_sync import router as cloud_sync_router
from .logs import router as logs_router

__all__ = [
    "projects_router",
    "vectors_router",
    "memory_router",
    "tables_router",
    "files_router",
    "events_router",
    "change_detection_router",
    "sync_state_router",
    "cloud_sync_router",
    "logs_router",
]
