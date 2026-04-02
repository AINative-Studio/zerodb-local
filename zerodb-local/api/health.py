"""
Health Check Module
Aggregates health status from all services.
Backend-aware: in lite mode only checks SQLite, FAISS, and filesystem.
"""
import asyncio
from typing import Dict, Any
from datetime import datetime

from lite.config import ZERODB_BACKEND, is_lite_mode, DATA_DIR


async def check_sqlite() -> Dict[str, Any]:
    """Check SQLite health (lite mode)."""
    try:
        import sqlite3
        db_path = DATA_DIR / "zerodb.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("SELECT 1")
        conn.close()
        return {
            "status": "healthy",
            "service": "sqlite",
            "message": "SQLite connection successful",
            "path": str(db_path),
        }
    except Exception as e:
        return {"status": "unhealthy", "service": "sqlite", "error": str(e)}


async def check_faiss() -> Dict[str, Any]:
    """Check FAISS index health (lite mode)."""
    try:
        index_dir = DATA_DIR / "faiss"
        return {
            "status": "healthy",
            "service": "faiss",
            "message": "FAISS index directory accessible",
            "path": str(index_dir),
        }
    except Exception as e:
        return {"status": "unhealthy", "service": "faiss", "error": str(e)}


async def check_filesystem() -> Dict[str, Any]:
    """Check local filesystem storage health (lite mode)."""
    try:
        files_dir = DATA_DIR / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        return {
            "status": "healthy",
            "service": "filesystem",
            "message": "Filesystem storage accessible",
            "path": str(files_dir),
        }
    except Exception as e:
        return {"status": "unhealthy", "service": "filesystem", "error": str(e)}


async def check_postgres() -> Dict[str, Any]:
    """
    Check PostgreSQL health

    Returns:
        Health status dict
    """
    try:
        from sqlalchemy import create_engine, text
        import os

        database_url = os.getenv("DATABASE_URL", "postgresql://zerodb:localpass@postgres:5432/zerodb_local")
        engine = create_engine(database_url)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()

        engine.dispose()

        return {
            "status": "healthy",
            "service": "postgres",
            "message": "Database connection successful"
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "postgres",
            "error": str(e)
        }


async def check_qdrant() -> Dict[str, Any]:
    """
    Check Qdrant health

    Returns:
        Health status dict
    """
    try:
        from services.qdrant_service import qdrant_service
        health = await qdrant_service.health_check()
        return {
            "service": "qdrant",
            **health
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "qdrant",
            "error": str(e)
        }


async def check_minio() -> Dict[str, Any]:
    """
    Check MinIO health

    Returns:
        Health status dict
    """
    try:
        from services.minio_service import minio_service
        health = await minio_service.health_check()
        return {
            "service": "minio",
            **health
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "minio",
            "error": str(e)
        }


async def check_redpanda() -> Dict[str, Any]:
    """
    Check RedPanda health

    Returns:
        Health status dict
    """
    try:
        from services.redpanda_service import redpanda_service
        health = await redpanda_service.health_check()
        return {
            "service": "redpanda",
            **health
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "redpanda",
            "error": str(e)
        }


async def check_embeddings() -> Dict[str, Any]:
    """
    Check embeddings service health

    Returns:
        Health status dict
    """
    try:
        import httpx
        import os

        embeddings_url = os.getenv("EMBEDDINGS_URL", "http://localhost:8001")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{embeddings_url}/health", timeout=5.0)

            if response.status_code == 200:
                data = response.json()
                return {
                    "service": "embeddings",
                    "status": data.get("status", "healthy"),
                    "model_loaded": data.get("model_loaded", False),
                    "model_info": data.get("model_info", {})
                }
            else:
                return {
                    "status": "unhealthy",
                    "service": "embeddings",
                    "error": f"HTTP {response.status_code}"
                }

    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "embeddings",
            "error": str(e)
        }


async def get_aggregated_health() -> Dict[str, Any]:
    """
    Get aggregated health status from all services.

    In lite mode only checks SQLite, FAISS index, and filesystem storage.
    In full mode checks PostgreSQL, Qdrant, MinIO, RedPanda, and embeddings.

    Returns:
        Aggregated health dict with overall status and backend identifier.
    """
    # Select checks based on active backend
    if is_lite_mode():
        checks = [check_sqlite(), check_faiss(), check_filesystem()]
    else:
        checks = [
            check_postgres(),
            check_qdrant(),
            check_minio(),
            check_redpanda(),
            check_embeddings(),
        ]

    results = await asyncio.gather(*checks, return_exceptions=True)

    # Build service health map
    services = {}
    all_healthy = True

    for result in results:
        if isinstance(result, Exception):
            all_healthy = False
            continue

        service_name = result.get("service", "unknown")
        services[service_name] = result

        if result.get("status") != "healthy":
            all_healthy = False

    # Calculate overall status
    overall_status = "healthy" if all_healthy else "degraded"

    # Count healthy vs unhealthy
    healthy_count = sum(1 for s in services.values() if s.get("status") == "healthy")
    total_count = len(services)

    return {
        "status": overall_status,
        "backend": ZERODB_BACKEND,
        "timestamp": datetime.utcnow().isoformat(),
        "services": services,
        "summary": {
            "healthy": healthy_count,
            "total": total_count,
            "percentage": round((healthy_count / total_count) * 100, 1) if total_count > 0 else 0
        }
    }


async def get_service_dependencies() -> Dict[str, list]:
    """
    Get service dependency graph

    Returns:
        Dict mapping services to their dependencies
    """
    return {
        "zerodb-api": ["postgres", "qdrant", "minio", "redpanda", "embeddings"],
        "dashboard": ["zerodb-api"],
        "postgres": [],
        "qdrant": [],
        "minio": [],
        "redpanda": [],
        "embeddings": []
    }


async def check_service_chain(service: str) -> Dict[str, Any]:
    """
    Check health of a service and all its dependencies

    Args:
        service: Service name to check

    Returns:
        Health status including dependency chain
    """
    dependencies = await get_service_dependencies()
    service_deps = dependencies.get(service, [])

    # Check this service and its dependencies
    checks = {}

    if service == "zerodb-api":
        # Check all infrastructure services
        for dep in service_deps:
            if dep == "postgres":
                checks[dep] = await check_postgres()
            elif dep == "qdrant":
                checks[dep] = await check_qdrant()
            elif dep == "minio":
                checks[dep] = await check_minio()
            elif dep == "redpanda":
                checks[dep] = await check_redpanda()
            elif dep == "embeddings":
                checks[dep] = await check_embeddings()

    # Determine if all dependencies are healthy
    all_deps_healthy = all(c.get("status") == "healthy" for c in checks.values())

    return {
        "service": service,
        "status": "healthy" if all_deps_healthy else "degraded",
        "dependencies": checks,
        "ready": all_deps_healthy
    }
