"""
Services Package
Exports all service instances for easy import.
Uses lazy imports to avoid eager instantiation.
When ZERODB_BACKEND=lite, heavy services are swapped for lightweight alternatives.
"""
from lite.config import is_lite_mode

__all__ = [
    "database_service",
    "qdrant_service",
    "minio_service",
    "redpanda_service",
    "embeddings_service",
    "vector_service",
    "memory_service",
    "events_service",
    "files_service",
    "tables_service",
    "CloudAPIClient",
]

# Mapping: full-mode service name -> (lite module path, lite object name)
# When lite mode is active, these services are loaded from the lite package.
_LITE_SERVICE_MAP = {
    "database_service": ("lite.services.database_service_lite", "database_service"),
    "qdrant_service": ("lite.services.faiss_service", "faiss_service"),
    "embeddings_service": ("lite.services.embeddings_service_local", "embeddings_service"),
    "minio_service": ("lite.services.filesystem_service", "filesystem_service"),
    "redpanda_service": ("lite.services.sqlite_events_service", "sqlite_events_service"),
}


def __getattr__(name):
    """Lazy import services on demand to avoid eager initialization.

    In lite mode, the services listed in _LITE_SERVICE_MAP are transparently
    replaced with their lightweight counterparts.
    """
    import importlib

    # If lite mode is active and this service has a lite replacement, use it.
    if is_lite_mode() and name in _LITE_SERVICE_MAP:
        module_path, attr_name = _LITE_SERVICE_MAP[name]
        mod = importlib.import_module(module_path)
        return getattr(mod, attr_name)

    # Full-mode (or services without a lite variant) -- original lazy loading.
    if name == "database_service":
        from .database_service import database_service
        return database_service
    elif name == "qdrant_service":
        from .qdrant_service import qdrant_service
        return qdrant_service
    elif name == "minio_service":
        from .minio_service import minio_service
        return minio_service
    elif name == "redpanda_service":
        from .redpanda_service import redpanda_service
        return redpanda_service
    elif name == "embeddings_service":
        from .embeddings_service import embeddings_service
        return embeddings_service
    elif name == "vector_service":
        from .vector_service import vector_service
        return vector_service
    elif name == "memory_service":
        from .memory_service import memory_service
        return memory_service
    elif name == "events_service":
        from .events_service import events_service
        return events_service
    elif name == "files_service":
        from .files_service import files_service
        return files_service
    elif name == "tables_service":
        from .tables_service import tables_service
        return tables_service
    elif name == "CloudAPIClient":
        from .cloud_client import CloudAPIClient
        return CloudAPIClient
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
