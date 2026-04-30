"""
ZeroDB Local - FastAPI Application
Main entry point for the local API server
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

# Import health check
from health import get_aggregated_health

# Import middleware
from middleware import setup_error_handlers

# Import routers
from routers import (
    projects_router,
    vectors_router,
    memory_router,
    tables_router,
    files_router,
    events_router,
    change_detection_router,
    sync_state_router,
    cloud_sync_router,
    logs_router
)
from routers.schema_diff import router as schema_diff_router
from routers.export import router as export_router
from routers.sync_orchestrator import router as sync_orchestrator_router
from routers.conflict_resolution import router as conflict_resolution_router
from routers.pull_sync import router as pull_sync_router
from routers.sync_history import router as sync_history_router

# Backend selector
from lite.config import ZERODB_BACKEND, DATA_DIR, is_lite_mode

# Environment variables
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
ENABLE_DOCS = os.getenv("ENABLE_DOCS", "true").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for FastAPI application
    Handles startup and shutdown events
    """
    # Startup
    print("=" * 60)
    print(f"Starting ZeroDB Local in {ZERODB_BACKEND} mode")
    print("=" * 60)
    print(f"Backend: {ZERODB_BACKEND}")
    print(f"Data directory: {DATA_DIR}")
    print(f"Debug mode: {DEBUG}")
    print(f"Log level: {LOG_LEVEL}")
    print(f"CORS origins: {CORS_ORIGINS}")
    print(f"API docs enabled: {ENABLE_DOCS}")
    print("=" * 60)

    # Initialize services (to be added in later stories)
    # await init_database()
    # await init_qdrant()
    # await init_minio()
    # await init_redpanda()

    print("✅ All services initialized")
    print("=" * 60)

    yield

    # Shutdown
    print("\n" + "=" * 60)
    print("ZeroDB Local API - Shutting down")
    print("=" * 60)


# Create FastAPI application
app = FastAPI(
    title="ZeroDB Local API",
    description="""
    ZeroDB Local - Self-hosted AI database with zero API costs.

    **Features:**
    - 🔒 Complete data sovereignty - all data stays local
    - 💰 Zero API costs - local embeddings with BAAI BGE models
    - 🚀 Full ZeroDB functionality - vectors, memory, tables, files, events
    - 🔄 Optional cloud sync - bi-directional sync with ZeroDB Cloud
    - 📦 Docker-based - one command to start everything
    - ⚡ Production-ready - PostgreSQL + Qdrant + MinIO + RedPanda

    **Authentication:**
    This local API reuses the same authentication infrastructure as ZeroDB Cloud,
    allowing you to use the same API keys and user accounts when syncing.

    **Endpoints:**
    - `/v1/projects/*` - Project management
    - `/v1/projects/{id}/database/vectors/*` - Vector operations
    - `/v1/projects/{id}/database/memory/*` - Agent memory
    - `/v1/projects/{id}/database/tables/*` - NoSQL tables
    - `/v1/projects/{id}/database/files/*` - File storage
    - `/v1/projects/{id}/database/events/*` - Event streaming
    - `/health` - Health checks (no auth required)
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
)

# Setup global error handlers
setup_error_handlers(app)

# CORS Middleware - Allow dashboard and other local services
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression for responses
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - API information
    """
    return {
        "service": "ZeroDB Local API",
        "version": "1.0.0",
        "status": "operational",
        "description": "Self-hosted AI database with zero API costs",
        "documentation": "/docs" if ENABLE_DOCS else "disabled",
        "features": [
            "Vector search (Qdrant)",
            "Agent memory (PostgreSQL + Qdrant)",
            "NoSQL tables (PostgreSQL)",
            "File storage (MinIO)",
            "Event streaming (RedPanda)",
            "Local embeddings (BAAI BGE)",
            "Optional cloud sync"
        ],
        "services": {
            "postgres": "postgresql://localhost:5432",
            "qdrant": "http://localhost:6333",
            "minio": "http://localhost:9000",
            "redpanda": "http://localhost:9092",
            "embeddings": "http://localhost:8001",
            "dashboard": "http://localhost:3000"
        }
    }


# Health check endpoint (no authentication required)
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Aggregated health check for all services

    Returns overall system health including:
    - PostgreSQL database status
    - Qdrant vector search status
    - MinIO object storage status
    - RedPanda event streaming status
    - Embeddings service status

    **Response:**
    - `status`: "healthy" or "degraded"
    - `services`: Health status per service
    - `summary`: Count of healthy vs total services
    """
    return await get_aggregated_health()


# Include routers at both /v1/ (local dev) and /api/v1/ (cloud sync compat)
for _prefix_base in ["/v1", "/api/v1"]:
    app.include_router(projects_router, prefix=f"{_prefix_base}/projects", tags=["Projects"])
    app.include_router(vectors_router, prefix=f"{_prefix_base}/projects/{{project_id}}/database/vectors", tags=["Vectors"])
    app.include_router(memory_router, prefix=f"{_prefix_base}/projects/{{project_id}}/database/memory", tags=["Memory"])
    app.include_router(tables_router, prefix=f"{_prefix_base}/projects/{{project_id}}/database/tables", tags=["Tables"])
    app.include_router(files_router, prefix=f"{_prefix_base}/projects/{{project_id}}/database/files", tags=["Files"])
    app.include_router(events_router, prefix=f"{_prefix_base}/projects/{{project_id}}/database/events", tags=["Events"])
    app.include_router(sync_state_router, prefix=f"{_prefix_base}/projects/{{project_id}}/sync", tags=["Sync State"])
    app.include_router(cloud_sync_router, prefix=f"{_prefix_base}/projects", tags=["Cloud Sync"])

# Sync/CDC router (not project-scoped)
app.include_router(change_detection_router, prefix="/v1/sync", tags=["Sync"])
app.include_router(schema_diff_router, prefix="/v1/sync/schema", tags=["Schema Diff"])

# Export router (project-level export bundle creation)
app.include_router(
    export_router,
    tags=["Export"]
)

# Sync Orchestrator router (core sync coordination)
app.include_router(
    sync_orchestrator_router,
    tags=["Sync Orchestrator"]
)

# Conflict Resolution router (nested under project sync)
app.include_router(
    conflict_resolution_router,
    tags=["Conflict Resolution"]
)

# Pull Sync router (cloud to local sync)
app.include_router(
    pull_sync_router,
    tags=["Pull Sync"]
)

# Sync History router (audit logging and history tracking)
app.include_router(
    sync_history_router,
    tags=["Sync History"]
)

# Logs router (system logs viewing)
app.include_router(
    logs_router,
    prefix="/v1",
    tags=["Logs"]
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG,
        log_level=LOG_LEVEL.lower()
    )
