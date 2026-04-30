# ZeroDB Local

> Run a full ZeroDB stack on your local machine — SQLite + FAISS (no Docker) or PostgreSQL + Qdrant + Docker for production-like environments.

[![PyPI version](https://badge.fury.io/py/zerodb-local.svg)](https://pypi.org/project/zerodb-local/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Quick Start — Lite Mode (No Docker, Recommended)

```bash
pip install zerodb-local[lite]
zerodb serve
```

Server starts at `http://localhost:8000` with:
- SQLite database
- FAISS vector search
- In-process embeddings (BAAI/bge-small-en-v1.5, 384 dims)
- Local filesystem storage

```bash
# Verify it works
curl http://localhost:8000/health

# Create a project
curl -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "my-project", "description": "Testing ZeroDB Local"}'
```

Data is stored at `~/.zerodb/data/` by default.

### CLI Options

```bash
zerodb serve                        # Start on port 8000
zerodb serve --port 9000            # Custom port
zerodb serve --data-dir /my/data    # Custom data directory
zerodb serve --cloud-key sk_...     # Enable cloud sync
```

---

## Installation

### Lite Mode (SQLite + FAISS)

```bash
pip install zerodb-local[lite]
```

### Full Mode (PostgreSQL + Qdrant + Docker)

```bash
pip install zerodb-local[full]
```

### Requirements

- Python 3.10+
- Docker 20.10+ and Docker Compose 2.0+ *(Full mode only)*
- 4GB RAM minimum (8GB recommended for Full mode)

---

## Full Mode (Docker)

Full mode runs PostgreSQL, Qdrant, MinIO, RedPanda, and a local embeddings service — mirrors the ZeroDB Cloud stack exactly.

```bash
# Clone and enter the zerodb-local directory
cd zerodb-local

# Copy environment template
cp .env.local.example .env.local

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

Services started:

| Service | Port | Purpose |
|---------|------|---------|
| API Server | 8000 | FastAPI — 128 endpoints matching ZeroDB Cloud |
| Dashboard | 3000 | React web UI |
| PostgreSQL + pgvector | 5432 | Relational + vector storage |
| Qdrant | 6333 | High-performance vector search |
| MinIO | 9000 | S3-compatible file storage |
| RedPanda | 9092 | Kafka-compatible event streaming |
| Embeddings | 8001 | Local BAAI/bge model inference |

**Dashboard:** http://localhost:3000  
**API docs:** http://localhost:8000/docs  
**API health:** http://localhost:8000/health

---

## Usage Examples

### Upsert a Vector

```bash
curl -X POST http://localhost:8000/v1/projects/{project_id}/database/vectors/upsert \
  -H "Content-Type: application/json" \
  -d '{
    "vector_embedding": [0.1, 0.2, 0.3],
    "document": "This is my document",
    "metadata": {"source": "local-test"}
  }'
```

### Semantic Search

```bash
curl -X POST http://localhost:8000/v1/projects/{project_id}/database/vectors/search \
  -H "Content-Type: application/json" \
  -d '{
    "query_vector": [0.1, 0.2, 0.3],
    "limit": 10,
    "threshold": 0.7
  }'
```

### Python SDK

```python
from zerodb_local import ZeroDBLocal

db = ZeroDBLocal()  # connects to http://localhost:8000

# Create project
project = db.projects.create(name="my-project")

# Upsert vector
db.vectors.upsert(
    project_id=project.id,
    document="Hello world",
    metadata={"source": "test"}
)

# Search
results = db.vectors.search(project_id=project.id, query="Hello", limit=5)
```

---

## CLI Reference

```bash
zerodb serve                    # Start local server (Lite mode)
zerodb serve --port 9000        # Custom port
zerodb local up                 # Start Full mode (Docker)
zerodb local down               # Stop Full mode
zerodb local status             # Check service health
zerodb cloud login              # Authenticate with ZeroDB Cloud
zerodb cloud link <project_id>  # Link local project to cloud
zerodb sync plan                # Preview what will sync
zerodb sync apply               # Push local data to cloud
zerodb cloud pull               # Pull cloud data locally
```

---

## Cloud Sync

Work offline locally, sync to [ZeroDB Cloud](https://ainative.studio) when ready.

1. Get your API key from https://ainative.studio/dashboard/api-keys
2. Add to `.env.local`: `CLOUD_API_KEY=sk_...`
3. Link and sync:

```bash
zerodb cloud login
zerodb cloud link <project_id>
zerodb sync apply
```

Conflict resolution options: `local-wins`, `cloud-wins`, `newest-wins`, `manual`

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              ZeroDB Local Stack              │
├─────────────────────────────────────────────┤
│  Dashboard (React)  ←→  API Server (FastAPI) │
│       :3000                  :8000           │
│                              │               │
│         ┌────────────────────┼──────────┐    │
│         ▼                   ▼          ▼    │
│   PostgreSQL+pgvector    Qdrant       MinIO  │
│        :5432              :6333       :9000  │
│                                             │
│   RedPanda (Events)   Embeddings (BAAI)     │
│        :9092               :8001            │
└─────────────────────────────────────────────┘
                    │ optional sync
                    ▼
         ZeroDB Cloud (api.ainative.studio)
```

---

## Configuration

Copy `.env.local.example` to `.env.local` and edit:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_PASSWORD` | `localpass` | **Change in production** |
| `CLOUD_API_KEY` | — | ZeroDB Cloud API key for sync |
| `EMBEDDINGS_MODEL` | `BAAI/bge-small-en-v1.5` | Embedding model (small/base/large) |
| `LOG_LEVEL` | `info` | debug / info / warning / error |
| `ZERODB_API_PORT` | `8000` | API server port |
| `ZERODB_DASHBOARD_PORT` | `3000` | Dashboard port |

All service ports are configurable via environment variables — see `.env.local.example` for the full list.

---

## Troubleshooting

**Services won't start**
```bash
docker-compose logs
docker-compose restart zerodb-api
```

**Port conflicts**
```bash
lsof -i :8000   # API
lsof -i :3000   # Dashboard
lsof -i :5432   # PostgreSQL
```
Update ports in `.env.local` or via `docker-compose.override.yml`.

**Slow embeddings** — use GPU if available:
```
EMBEDDINGS_DEVICE=cuda
```

**Full reset**
```bash
docker-compose down -v && rm -rf ./data && docker-compose up -d
```

---

## Performance

| Operation | Lite (SQLite+FAISS) | Full (PG+Qdrant) |
|-----------|---------------------|------------------|
| Vector upsert | <20ms | <10ms |
| Semantic search (10k vectors) | <100ms | <50ms |
| Embeddings generation | <200ms | <100ms |

Lite mode scales to ~100k vectors comfortably. Full mode handles 1M+.

---

## Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/my-feature`
3. Run tests: `cd zerodb-local && pytest tests/ -v`
4. Open a PR

---

## Support

- **Docs:** https://docs.ainative.studio
- **Issues:** https://github.com/AINative-Studio/zerodb-local/issues
- **Community:** https://ainative.studio/community
- **Email:** hello@ainative.studio

## License

MIT — see [LICENSE](zerodb-local/LICENSE)
