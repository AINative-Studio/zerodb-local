# ZeroDB Local

Run ZeroDB on your local machine. Two modes available:
- **Lite mode** (recommended) — pip install, no Docker required
- **Full mode** — Docker Compose with PostgreSQL, Qdrant, MinIO, RedPanda

## Quick Start — Lite Mode (No Docker)

```bash
pip install zerodb-local[lite]
zerodb serve
```

That's it. Server starts at `http://localhost:8000` with:
- SQLite database
- FAISS vector search
- In-process embeddings (BAAI/bge-small-en-v1.5, 384 dims)
- Local filesystem storage
- SQLite event queue

### Verify it works

```bash
# Health check
curl http://localhost:8000/health

# Create a project
curl -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "my-project", "description": "Testing ZeroDB Local"}'
```

### CLI Options

```bash
zerodb serve                        # Start on port 8000
zerodb serve --port 9000            # Custom port
zerodb serve --data-dir /my/data    # Custom data directory
zerodb serve --cloud-key sk_...     # Enable cloud sync
```

Data is stored at `~/.zerodb/data/` by default.

## Features

- **Two backends**: Lite (SQLite + FAISS) or Full (PostgreSQL + Qdrant + Docker)
- **Local API Server**: Mirrors all 128 ZeroDB Cloud endpoints
- **Web Dashboard**: Manage projects, vectors, tables, files, and events via UI
- **CLI Tool**: `zerodb` command for local control and cloud sync
- **Offline-First**: Work without internet, sync when ready
- **No API Costs**: Local embeddings using BAAI BGE models (free)
- **Cloud Sync**: Bidirectional sync with ZeroDB Cloud
- **Production-Ready**: Same code paths as cloud for consistency

---

## Full Mode (Docker)

For production-like environments with PostgreSQL, Qdrant, MinIO, and RedPanda.

### Prerequisites

- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Python** 3.11+ (for CLI tool)
- At least 4GB RAM available for Docker

### Installation

1. **Clone the repository**:
   ```bash
   cd zerodb-local
   ```

2. **Copy environment template**:
   ```bash
   cp .env.local.example .env.local
   ```

3. **Edit `.env.local`** (optional):
   - Update `POSTGRES_PASSWORD` for production use
   - Set `CLOUD_API_KEY` if you want cloud sync
   - Adjust `EMBEDDINGS_MODEL` based on your needs

4. **Start all services**:
   ```bash
   docker-compose up -d
   ```

5. **Verify services are running**:
   ```bash
   docker-compose ps
   ```

   You should see 7 services running:
   - `zerodb-postgres` (PostgreSQL + pgvector)
   - `zerodb-qdrant` (Vector search)
   - `zerodb-minio` (Object storage)
   - `zerodb-redpanda` (Event streaming)
   - `zerodb-embeddings` (Local embeddings)
   - `zerodb-api` (API server)
   - `zerodb-dashboard` (Web UI)

6. **Access the dashboard**:
   - Open http://localhost:3000 in your browser

7. **Check API health**:
   ```bash
   curl http://localhost:8000/health
   ```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ZeroDB Local Stack                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐         ┌──────────────┐                   │
│  │  Dashboard  │◄────────┤   API Server │                   │
│  │ (React UI)  │  REST   │   (FastAPI)  │                   │
│  └─────────────┘         └───────┬──────┘                   │
│   localhost:3000                 │                           │
│                                  │                           │
│          ┌───────────────────────┼───────────────────┐       │
│          │                       │                   │       │
│          ▼                       ▼                   ▼       │
│  ┌──────────────┐      ┌─────────────┐     ┌─────────────┐  │
│  │  PostgreSQL  │      │   Qdrant    │     │    MinIO    │  │
│  │  + pgvector  │      │  (Vectors)  │     │   (Files)   │  │
│  └──────────────┘      └─────────────┘     └─────────────┘  │
│   localhost:5432        localhost:6333      localhost:9000  │
│                                                              │
│          ┌───────────────────────┬──────────────────┐        │
│          │                       │                  │        │
│          ▼                       ▼                  ▼        │
│  ┌──────────────┐      ┌─────────────┐     ┌─────────────┐  │
│  │   RedPanda   │      │ Embeddings  │     │    CLI      │  │
│  │   (Events)   │      │   (BAAI)    │     │   (Typer)   │  │
│  └──────────────┘      └─────────────┘     └─────────────┘  │
│   localhost:9092        localhost:8001      zerodb command  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Sync (optional)
                            ▼
                  ┌─────────────────────┐
                  │  ZeroDB Cloud API   │
                  │ api.ainative.studio │
                  └─────────────────────┘
```

## Services

### PostgreSQL + pgvector (Port 5432)
- **Purpose**: Relational data storage with vector support
- **Storage**: `./data/postgres`
- **Console**: Access via `psql` or any PostgreSQL client
- **Usage**: Tables, metadata, change logs

### Qdrant (Port 6333)
- **Purpose**: High-performance vector similarity search
- **Storage**: `./data/qdrant`
- **Web UI**: http://localhost:6333/dashboard
- **Usage**: Fast semantic search for vectors and memory

### MinIO (Port 9000/9001)
- **Purpose**: S3-compatible object storage
- **Storage**: `./data/minio`
- **Console**: http://localhost:9001 (minioadmin/minioadmin)
- **Usage**: File uploads, large blobs

### RedPanda (Port 9092)
- **Purpose**: Kafka-compatible event streaming
- **Storage**: `./data/redpanda`
- **Console**: http://localhost:9644
- **Usage**: Event sourcing, CDC, real-time notifications

### Embeddings Service (Port 8001)
- **Purpose**: Local text embedding generation
- **Model**: BAAI/bge-small-en-v1.5 (384 dimensions)
- **Storage**: `./data/embeddings/models`
- **Usage**: Generate embeddings without API costs

### API Server (Port 8000)
- **Purpose**: FastAPI server mirroring ZeroDB Cloud
- **Endpoints**: 128 endpoints matching cloud API
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

### Dashboard (Port 3000)
- **Purpose**: Web UI for local management
- **Framework**: React 18 + TypeScript + Vite
- **Features**: Projects, vectors, tables, files, events, sync

## Usage Examples

### Create a Project
```bash
curl -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-first-project",
    "description": "Testing ZeroDB Local"
  }'
```

### Upsert a Vector
```bash
curl -X POST http://localhost:8000/v1/projects/{project_id}/database/vectors/upsert \
  -H "Content-Type: application/json" \
  -d '{
    "vector_embedding": [0.1, 0.2, 0.3, ...],
    "document": "This is my document",
    "metadata": {"source": "local-test"}
  }'
```

### Search Vectors
```bash
curl -X POST http://localhost:8000/v1/projects/{project_id}/database/vectors/search \
  -H "Content-Type: application/json" \
  -d '{
    "query_vector": [0.1, 0.2, 0.3, ...],
    "limit": 10,
    "threshold": 0.7
  }'
```

## CLI Tool

### Installation
```bash
cd cli
pip install -e .
```

### Commands
```bash
# Start local environment
zerodb local up

# Stop local environment
zerodb local down

# Check service status
zerodb local status

# Login to cloud
zerodb cloud login

# Link local project to cloud
zerodb cloud link <project_id>

# Sync to cloud (push)
zerodb sync apply

# Pull from cloud
zerodb cloud pull
```

## Data Management

### Backup Local Data
```bash
./scripts/backup-local.sh
```

Creates backup in `./backups/zerodb-backup-YYYY-MM-DD.tar.gz`

### Restore from Backup
```bash
./scripts/restore-local.sh ./backups/zerodb-backup-YYYY-MM-DD.tar.gz
```

### Reset Everything
```bash
docker-compose down -v
rm -rf ./data
docker-compose up -d
```

## Development

### Hot Reload API
```bash
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Hot Reload Dashboard
```bash
cd dashboard
npm run dev
```

### Run Tests
```bash
cd api
pytest tests/ -v --cov
```

## Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs

# Restart specific service
docker-compose restart zerodb-api

# Full reset
docker-compose down -v && docker-compose up -d
```

### Port conflicts
```bash
# Check what's using the ports
lsof -i :5432   # PostgreSQL
lsof -i :6333   # Qdrant
lsof -i :9000   # MinIO
lsof -i :9092   # RedPanda
lsof -i :8000   # API
lsof -i :3000   # Dashboard

# Update ports in docker-compose.yml if needed
```

### Slow embeddings
```bash
# Use GPU if available (NVIDIA)
# Update .env.local:
EMBEDDINGS_DEVICE=cuda

# Or use larger model (slower but more accurate)
EMBEDDINGS_MODEL=BAAI/bge-base-en-v1.5  # 768 dims
EMBEDDINGS_MODEL=BAAI/bge-large-en-v1.5  # 1024 dims
```

### Database connection issues
```bash
# Check Postgres is healthy
docker-compose exec postgres pg_isready

# Inspect logs
docker-compose logs postgres

# Connect manually
docker-compose exec postgres psql -U zerodb -d zerodb_local
```

## Cloud Sync

### Setup
1. Get your API key from https://www.ainative.studio/dashboard/api-keys
2. Add to `.env.local`:
   ```
   CLOUD_API_KEY=your-api-key-here
   ```
3. Login via CLI:
   ```bash
   zerodb cloud login
   ```

### Sync Workflow
```bash
# 1. Make changes locally (add vectors, tables, etc.)

# 2. See what will be synced
zerodb sync plan

# 3. Push to cloud
zerodb sync apply

# 4. Pull changes from cloud
zerodb cloud pull
```

### Conflict Resolution
Configure in `.env.local`:
```
CONFLICT_RESOLUTION=newest-wins  # local-wins, cloud-wins, newest-wins, manual
```

## Environment Variables Reference

See `.env.local.example` for complete list. Key variables:

- `POSTGRES_PASSWORD` - Database password (change in production!)
- `CLOUD_API_KEY` - Your ZeroDB Cloud API key for sync
- `EMBEDDINGS_MODEL` - Model to use (small/base/large)
- `LOG_LEVEL` - Logging verbosity (debug/info/warning/error)
- `DEBUG` - Enable debug mode (true/false)

## System Requirements

### Minimum
- 4GB RAM
- 10GB disk space
- 2 CPU cores
- Docker 20.10+

### Recommended
- 8GB RAM
- 50GB disk space (for embeddings models + data)
- 4 CPU cores
- SSD storage
- Docker 24.0+

## Performance

### Expected Latency
- Vector upsert: <10ms
- Semantic search (10k vectors): <50ms
- Embeddings generation: <100ms per text
- Sync (1k vectors): <30s

### Scaling Limits (Local)
- Vectors: Up to 1M (limited by RAM)
- Tables: Unlimited (limited by disk)
- Files: Unlimited (limited by disk)
- Events: 10k/sec (limited by RedPanda)

## Security

### Default Credentials
**⚠️ CHANGE THESE IN PRODUCTION!**
- PostgreSQL: `zerodb` / `localpass`
- MinIO: `minioadmin` / `minioadmin`
- API JWT Secret: (generated automatically)

### Best Practices
1. Use strong passwords in `.env.local`
2. Never commit `.env.local` to git
3. Use API keys for cloud sync (not passwords)
4. Enable HTTPS for remote access
5. Restrict CORS origins in production

## Documentation

- **Quick Start**: [docs/QUICK_START.md](./docs/QUICK_START.md) - Step-by-step setup guide
- **Environment Setup**: [docs/ENVIRONMENT_SETUP.md](./docs/ENVIRONMENT_SETUP.md) - Configuration for local/staging/production
- **Data Management**: [docs/DATA_MANAGEMENT.md](./docs/DATA_MANAGEMENT.md) - Backups, restores, and data lifecycle
- **Troubleshooting**: [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md) - Common issues and solutions
- **Sync Strategy**: [docs/SYNC_STRATEGY.md](./docs/SYNC_STRATEGY.md) - Cloud sync configuration
- **API Reference**: http://localhost:8000/docs - Interactive API documentation

## Port Configuration

All external port mappings in `docker-compose.yml` are configurable via environment variables. Each defaults to the standard port if unset.

| Service | Default Port | Environment Variable |
|---------|-------------|---------------------|
| PostgreSQL | 5432 | `ZERODB_POSTGRES_PORT` |
| Qdrant REST | 6333 | `ZERODB_QDRANT_REST_PORT` |
| Qdrant gRPC | 6334 | `ZERODB_QDRANT_GRPC_PORT` |
| MinIO API | 9000 | `ZERODB_MINIO_API_PORT` |
| MinIO Console | 9001 | `ZERODB_MINIO_CONSOLE_PORT` |
| RedPanda Kafka | 9092 | `ZERODB_REDPANDA_KAFKA_PORT` |
| RedPanda HTTP Proxy | 8082 | `ZERODB_REDPANDA_PROXY_PORT` |
| RedPanda Admin | 9644 | `ZERODB_REDPANDA_ADMIN_PORT` |
| Embeddings | 8001 | `ZERODB_EMBEDDINGS_PORT` |
| API Server | 8000 | `ZERODB_API_PORT` |
| Dashboard | 3000 | `ZERODB_DASHBOARD_PORT` |

### Remapping Ports

Set variables in your `.env.local` file or pass them directly:

```bash
# Via .env.local
ZERODB_API_PORT=8080
ZERODB_DASHBOARD_PORT=3001
ZERODB_POSTGRES_PORT=5433

# Or inline
ZERODB_API_PORT=8080 docker-compose up -d
```

### Using docker-compose.override.yml

For persistent local overrides without modifying tracked files, create a `docker-compose.override.yml`:

```yaml
version: '3.8'
services:
  zerodb-api:
    ports:
      - "8080:8000"
  dashboard:
    ports:
      - "3001:3000"
  postgres:
    ports:
      - "5433:5432"
```

Docker Compose automatically merges this file with `docker-compose.yml` on every `docker-compose up`.

### Port Conflict Detection

The `port-config.json` file in this directory describes all service ports and their env vars. It can be consumed by the port-management skill or any automation tool to detect conflicts before starting the stack.

## Support

- **GitHub Issues**: https://github.com/AINative-Studio/core/issues
- **Documentation**: https://www.ainative.studio/docs
- **Community**: https://www.ainative.studio/community
- **Email**: hello@ainative.studio

## License

MIT License. See [LICENSE](./LICENSE) for details.

---

**Built with ❤️ by the AINative Studio team**
