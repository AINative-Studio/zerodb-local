# ZeroDB Local

Run ZeroDB on your own machine: vectors, tables, agent memory, files and events behind the same API as ZeroDB Cloud, plus a web dashboard to manage it all.

Two ways to run it:
- **Lite mode** (recommended to start): `pip install`, no Docker. SQLite + FAISS + local files.
- **Full mode**: Docker Compose with PostgreSQL, Qdrant, MinIO and RedPanda.

**At a glance**

| | Lite mode | Full mode (Docker) |
|---|---|---|
| API | http://localhost:8000 | http://localhost:8000 |
| API docs | http://localhost:8000/docs | http://localhost:8000/docs |
| Dashboard | http://localhost:3000 (run it yourself, below) | http://localhost:3000 (starts with Compose) |
| Sign-in | **None.** Every request acts as a built-in local user | **ZeroDB API key** by default (`ZERODB_AUTH_MODE=cloud`) |
| Data | `~/.zerodb/data/` | Docker volumes |

---

## Quick start: lite mode (no Docker)

**Needs:** Python 3.11+. For the dashboard, also Node.js 20+.

### 1. Start the API

```bash
pip install "zerodb-local[lite]"
zerodb serve
```

The API is now at **http://localhost:8000**, with:
- SQLite database
- FAISS vector search
- In-process embeddings (BAAI/bge-small-en-v1.5, 384 dims). The model downloads once on first use (~130 MB), so the first vector upsert takes a little longer.
- Local filesystem storage
- SQLite event queue

Check it:

```bash
curl http://localhost:8000/health
```

### 2. Start the dashboard

The dashboard ships in this repo (it isn't part of the pip package):

```bash
git clone https://github.com/AINative-Studio/zerodb-local.git
cd zerodb-local/dashboard
cp .env.example .env.local      # points the dashboard at http://localhost:8000
npm ci
npm run dev
```

Open **http://localhost:3000**. Use `localhost`, not `127.0.0.1`: the API only accepts browser requests from `http://localhost:3000` by default (set `CORS_ORIGINS` on the API to change that).

From there you can do everything without the CLI or curl: create a project, add vectors and tables, store agent memory, upload files, publish events and sync to the cloud.

### Options

```bash
zerodb serve --port 9000                         # different API port
zerodb serve --host 127.0.0.1                    # only reachable from this machine
ZERODB_DATA_DIR=/my/data zerodb serve            # different data folder
CLOUD_API_KEY=sk_... zerodb serve                # enable cloud sync
```

If you change the API port, set `NEXT_PUBLIC_API_URL` in `dashboard/.env.local` to match and restart `npm run dev`.

When running from a source checkout, `zerodb serve` also accepts `--data-dir` and `--cloud-key`.

---

## Sign-in, users and default passwords

**Lite mode has no login.** There's no user account to create and no password. Every request is treated as one built-in local user:

| Setting | Default | Override with |
|---|---|---|
| User ID | `00000000-0000-0000-0000-000000000001` | `ZERODB_USER_ID` |
| Email | `dev@localhost` | `ZERODB_USER_EMAIL` |
| Username | `local-developer` | `ZERODB_USERNAME` |

**Full mode (Docker) requires a ZeroDB API key by default** (`ZERODB_AUTH_MODE=cloud`). Either set `CLOUD_API_KEY` in `.env.local`, or open the dashboard and paste your key in **Settings › Connection**. The dashboard keeps it in your browser and sends it as `Authorization: Bearer <key>`; if the API turns a request down, the dashboard shows a banner pointing you there. Set `ZERODB_AUTH_MODE=local` to switch full mode to no-login like lite mode. Get a key at https://www.ainative.studio/dashboard/api-keys.

**Default service credentials (full mode only).** These are for the containers, not for you to log in to the dashboard. Change them in `.env.local` before exposing anything beyond your machine:

| Service | Username | Password |
|---|---|---|
| PostgreSQL (`localhost:5432`, db `zerodb_local`) | `zerodb` | `localpass` |
| MinIO console (http://localhost:9001) | `minioadmin` | `minioadmin` |

> **Security note.** In no-login mode, anyone who can reach the API's port can read, change and delete everything. `zerodb serve` listens on all network interfaces (`0.0.0.0`) by default, so on shared Wi-Fi other people on the network can reach it. Use `zerodb serve --host 127.0.0.1` unless you mean to share it, and don't forward these ports to the internet.

---

## Ports

| Port | What | Mode | Change with |
|---|---|---|---|
| **8000** | ZeroDB API (+ `/docs`, `/health`) | both | `zerodb serve --port`, or `ZERODB_API_PORT` |
| **3000** | Dashboard | both | `npm run dev -- -p <port>`, or `ZERODB_DASHBOARD_PORT` |
| 8001 | Embeddings service | full | `ZERODB_EMBEDDINGS_PORT` |
| 5432 | PostgreSQL | full | `ZERODB_POSTGRES_PORT` |
| 6333 / 6334 | Qdrant REST / gRPC | full | `ZERODB_QDRANT_REST_PORT` / `ZERODB_QDRANT_GRPC_PORT` |
| 9000 / 9001 | MinIO API / console | full | `ZERODB_MINIO_API_PORT` / `ZERODB_MINIO_CONSOLE_PORT` |
| 9092 / 8082 / 9644 | RedPanda Kafka / proxy / admin | full | `ZERODB_REDPANDA_*_PORT` |

If you move the dashboard to another port, add it to the API's `CORS_ORIGINS` (comma-separated).

---

## The dashboard

| Page | What you can do |
|---|---|
| Overview | See which backend is running (lite/full) and its health, totals across projects, your API endpoint, recent activity |
| Projects | Create, search and delete projects. Everything else lives inside a project |
| Vectors | Upsert text (embedded for you, free), search by meaning, filter by namespace, delete |
| Tables | Create tables with a column builder or a JSON schema, add rows, browse, delete |
| Memory | Browse agent conversations by session, search memory by meaning, add or delete memories |
| Files | Upload (drag and drop), download, delete |
| Events | Live feed filtered by type, event details, publish test events |
| Sync | See what's waiting, preview a push/pull plan, run it, resolve conflicts, view history |
| Logs | Live server logs with level, service and time filters; export |
| Settings | Light/dark/system theme, server details, API key, create-form defaults, cloud connection |

Every create form opens in a guided mode with plain-language fields, with an **Advanced JSON** switch that shows the exact API request.

## Features

- **Two backends**: Lite (SQLite + FAISS) or Full (PostgreSQL + Qdrant + Docker)
- **Local API Server**: Mirrors the ZeroDB Cloud API
- **Web Dashboard**: Manage projects, vectors, tables, memory, files, events and sync via UI
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
   - Set `CLOUD_API_KEY` (needed for the default cloud sign-in and for cloud sync), or set `ZERODB_AUTH_MODE=local` for no login
   - Change `POSTGRES_PASSWORD` and the MinIO keys from their defaults
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
   - If you kept cloud sign-in, paste your API key in **Settings › Connection**

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
- **Framework**: Next.js 14 (App Router) + React 18 + TypeScript + Tailwind
- **Features**: Projects, vectors, tables, memory, files, events, sync, logs, settings (see [The dashboard](#the-dashboard))

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

In full mode with cloud sign-in, add `-H "Authorization: Bearer $CLOUD_API_KEY"` to each request. Lite mode needs no header.

### Upsert a Vector
The API embeds `document` for you (free, local model). Reusing a `vector_id` replaces that vector.
```bash
curl -X POST http://localhost:8000/v1/projects/{project_id}/database/vectors/upsert \
  -H "Content-Type: application/json" \
  -d '{
    "document": "Refunds are issued within 5 business days.",
    "namespace": "faq",
    "vector_id": "faq-refunds",
    "metadata": {"topic": "billing"}
  }'
```

### Search Vectors
Search by meaning with plain text:
```bash
curl -X POST http://localhost:8000/v1/projects/{project_id}/database/vectors/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "how long do refunds take",
    "namespace": "faq",
    "limit": 10,
    "threshold": 0.3
  }'
```

### Store and recall agent memory
```bash
curl -X POST http://localhost:8000/v1/projects/{project_id}/database/memory/store \
  -H "Content-Type: application/json" \
  -d '{"content": "Prefers annual billing", "role": "user", "agent_id": "support", "session_id": "chat-42"}'

curl -X POST http://localhost:8000/v1/projects/{project_id}/database/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "billing preference", "agent_id": "support"}'
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
# API
cd api
pytest tests/ -v --cov

# Dashboard
cd dashboard
npm test              # unit + page tests (Vitest)
npm run type-check
npm run lint
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

### Dashboard shows "This server needs an API key"
The API is in cloud sign-in mode (the full-mode default). Paste your ZeroDB API key in **Settings › Connection**, or set `ZERODB_AUTH_MODE=local` in `.env.local` and restart the API.

### Dashboard can't reach the API
- Is the API running? `curl http://localhost:8000/health`
- Open the dashboard at `http://localhost:3000`, not `127.0.0.1` (CORS)
- Changed the API port? Update `NEXT_PUBLIC_API_URL` in `dashboard/.env.local` (or rebuild the Docker dashboard image)

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
In the dashboard: **Sync** page → choose Push / Pull / Both → **Preview sync** → review → **Run sync**.

From the CLI:
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

See [SUPPORT.md](./SUPPORT.md) for how to get help, report a bug, or
request a feature.

## License

MIT License. See [LICENSE](./LICENSE) for details.

---

**Built with ❤️ by the AINative Studio team**
