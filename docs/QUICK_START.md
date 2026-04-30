# ZeroDB Local - Quick Start Guide

Get up and running with ZeroDB Local in under 15 minutes. This guide walks you through installation, verification, and your first API calls.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Verification](#verification)
- [First Steps](#first-steps)
- [Usage Examples](#usage-examples)
- [CLI Tool Setup](#cli-tool-setup)
- [Dashboard Tour](#dashboard-tour)
- [Next Steps](#next-steps)

## Prerequisites

Before you begin, ensure you have the following installed on your machine:

### Required Software

| Software | Minimum Version | Recommended Version | Download |
|----------|----------------|---------------------|----------|
| Docker | 20.10+ | 24.0+ | https://www.docker.com/get-started |
| Docker Compose | 2.0+ | 2.20+ | Included with Docker Desktop |
| Node.js | 20+ | 20 LTS | https://nodejs.org |
| Python | 3.11+ | 3.11+ | https://www.python.org/downloads |

### System Requirements

**Minimum:**
- 4GB RAM available for Docker
- 10GB free disk space
- 2 CPU cores
- macOS 11+, Ubuntu 20.04+, or Windows 10+ with WSL2

**Recommended:**
- 8GB RAM
- 50GB free disk space (for embeddings models and data)
- 4 CPU cores
- SSD storage for better performance

### Port Availability

ZeroDB Local requires the following ports to be available:

| Port | Service | Purpose |
|------|---------|---------|
| 3000 | Dashboard | Web UI for managing ZeroDB |
| 5432 | PostgreSQL | Relational database with pgvector |
| 6333 | Qdrant | Vector search engine |
| 8000 | API Server | FastAPI REST API |
| 8001 | Embeddings | Local embedding generation service |
| 9000 | MinIO API | S3-compatible object storage |
| 9001 | MinIO Console | MinIO web interface |
| 9092 | RedPanda | Kafka-compatible event streaming |
| 9644 | RedPanda Console | RedPanda web interface |

**Check for port conflicts:**
```bash
# macOS/Linux
lsof -i :3000 -i :5432 -i :6333 -i :8000 -i :8001 -i :9000 -i :9001 -i :9092 -i :9644

# Windows (PowerShell)
netstat -ano | findstr "3000 5432 6333 8000 8001 9000 9001 9092 9644"
```

If any ports are in use, you can either:
1. Stop the conflicting service
2. Edit `docker-compose.yml` to use different ports (see [Environment Setup](./ENVIRONMENT_SETUP.md))

## Installation

### Step 1: Clone or Navigate to Repository

If you're working with the AINative Studio core repository:

```bash
cd /Users/aideveloper/core/zerodb-local
```

Or if you're cloning separately:

```bash
git clone https://github.com/AINative-Studio/core.git
cd core/zerodb-local
```

### Step 2: Create Environment Configuration

ZeroDB Local uses environment variables for configuration. Start by copying the example file:

```bash
cp .env.local.example .env.local
```

### Step 3: Configure Environment (Optional)

For most development use cases, the default configuration works out of the box. However, you should update the following for production use:

```bash
# Open .env.local in your editor
nano .env.local  # or vim, code, etc.
```

**Key variables to review:**

```env
# Database - CHANGE IN PRODUCTION!
POSTGRES_PASSWORD=localpass  # Use a strong password for production

# Cloud Sync (optional)
CLOUD_API_KEY=  # Add your API key if you want cloud sync

# Embeddings Model
EMBEDDINGS_MODEL=BAAI/bge-small-en-v1.5  # Options: small/base/large
EMBEDDINGS_DEVICE=cpu  # Options: cpu, cuda (NVIDIA GPU), mps (Apple Silicon)

# Logging
LOG_LEVEL=info  # Options: debug, info, warning, error
DEBUG=false  # Set to true for verbose debugging
```

For detailed configuration options, see [Environment Setup](./ENVIRONMENT_SETUP.md).

### Step 4: Start All Services

Launch the entire ZeroDB Local stack with a single command:

```bash
docker-compose up -d
```

This will:
1. Pull Docker images (first time only, ~5-10 minutes)
2. Create Docker volumes for persistent storage
3. Start all 7 services in the background

**What the `-d` flag does:**
- Runs containers in detached mode (background)
- Allows you to continue using your terminal
- Logs are still accessible via `docker-compose logs`

### Step 5: Monitor Startup Progress

Watch the logs to ensure all services start successfully:

```bash
# Follow all logs
docker-compose logs -f

# Or follow a specific service
docker-compose logs -f zerodb-api
```

**Press Ctrl+C to stop following logs** (services continue running in background)

### Step 6: Verify Service Health

Check that all services are running:

```bash
docker-compose ps
```

**Expected output:**

```
NAME                     IMAGE                                    STATUS
zerodb-api              zerodb-local-api                         Up 2 minutes (healthy)
zerodb-dashboard        zerodb-local-dashboard                   Up 2 minutes
zerodb-embeddings       zerodb-local-embeddings                  Up 2 minutes (healthy)
zerodb-minio            minio/minio:latest                       Up 2 minutes (healthy)
zerodb-postgres         ankane/pgvector:latest                   Up 2 minutes (healthy)
zerodb-qdrant           qdrant/qdrant:latest                     Up 2 minutes (healthy)
zerodb-redpanda         vectorized/redpanda:latest               Up 2 minutes
```

**All services should show "Up" status.** If any service shows "Restarting" or "Exited", see [Troubleshooting](./TROUBLESHOOTING.md).

## Verification

### Health Checks

Verify each service is responding:

```bash
# API Server
curl http://localhost:8000/health
# Expected: {"status": "healthy", "version": "1.0.0"}

# Embeddings Service
curl http://localhost:8001/health
# Expected: {"status": "ready", "model": "BAAI/bge-small-en-v1.5"}

# Qdrant
curl http://localhost:6333/
# Expected: {"title": "qdrant - vector search engine", ...}

# MinIO
curl http://localhost:9000/minio/health/live
# Expected: (empty 200 response)
```

### Web Interfaces

Open the following URLs in your browser to verify web interfaces:

| Service | URL | Credentials |
|---------|-----|-------------|
| Dashboard | http://localhost:3000 | No login required (local only) |
| API Docs | http://localhost:8000/docs | No login required |
| Qdrant Dashboard | http://localhost:6333/dashboard | No login required |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| RedPanda Console | http://localhost:9644 | No login required |

### Database Connection Test

Test PostgreSQL connectivity:

```bash
docker-compose exec postgres pg_isready -U zerodb -d zerodb_local
```

**Expected output:**
```
/var/run/postgresql:5432 - accepting connections
```

## First Steps

### 1. Access the Dashboard

Open http://localhost:3000 in your browser. You should see the ZeroDB Local dashboard with:

- **Projects** tab (currently empty)
- **Vectors** tab
- **Tables** tab
- **Files** tab
- **Events** tab
- **Sync** tab

### 2. Create Your First Project

**Via Dashboard:**
1. Click "Projects" in the sidebar
2. Click "New Project" button
3. Enter project details:
   - Name: `my-first-project`
   - Description: `Testing ZeroDB Local`
4. Click "Create Project"

**Via API:**
```bash
curl -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-first-project",
    "description": "Testing ZeroDB Local"
  }'
```

**Response:**
```json
{
  "id": "proj_1a2b3c4d5e6f",
  "name": "my-first-project",
  "description": "Testing ZeroDB Local",
  "created_at": "2026-02-27T15:00:00Z",
  "updated_at": "2026-02-27T15:00:00Z"
}
```

Save the `id` value - you'll need it for subsequent API calls.

### 3. Generate Your First Embedding

Use the local embeddings service to convert text into a vector:

```bash
curl -X POST http://localhost:8001/embed \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is my first ZeroDB document!"
  }'
```

**Response:**
```json
{
  "embedding": [0.123, -0.456, 0.789, ...],  // 384 dimensions
  "model": "BAAI/bge-small-en-v1.5",
  "dimensions": 384
}
```

### 4. Upsert Your First Vector

Store a document with its embedding in the vector database:

```bash
# Replace {project_id} with your actual project ID
curl -X POST http://localhost:8000/v1/projects/{project_id}/database/vectors/upsert \
  -H "Content-Type: application/json" \
  -d '{
    "vector_embedding": [0.123, -0.456, 0.789, ...],  # Use embedding from step 3
    "document": "Hello, this is my first ZeroDB document!",
    "metadata": {
      "source": "quick-start-guide",
      "timestamp": "2026-02-27T15:00:00Z"
    }
  }'
```

**Response:**
```json
{
  "id": "vec_1a2b3c4d5e6f",
  "status": "upserted",
  "operation": "created"
}
```

### 5. Search for Similar Vectors

Search for documents similar to a query:

```bash
# First, generate embedding for your query
QUERY_EMBEDDING=$(curl -s -X POST http://localhost:8001/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "greeting message"}' | jq -r '.embedding')

# Then search
curl -X POST http://localhost:8000/v1/projects/{project_id}/database/vectors/search \
  -H "Content-Type: application/json" \
  -d "{
    \"query_vector\": $QUERY_EMBEDDING,
    \"limit\": 10,
    \"threshold\": 0.7
  }"
```

**Response:**
```json
{
  "results": [
    {
      "id": "vec_1a2b3c4d5e6f",
      "score": 0.95,
      "document": "Hello, this is my first ZeroDB document!",
      "metadata": {
        "source": "quick-start-guide",
        "timestamp": "2026-02-27T15:00:00Z"
      }
    }
  ],
  "total": 1
}
```

## Usage Examples

### Working with Tables (NoSQL)

**Create a table:**
```bash
curl -X POST http://localhost:8000/v1/projects/{project_id}/database/tables/create \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "users",
    "schema": {
      "id": "string",
      "name": "string",
      "email": "string",
      "created_at": "timestamp"
    }
  }'
```

**Insert rows:**
```bash
curl -X POST http://localhost:8000/v1/projects/{project_id}/database/tables/users/insert \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [
      {
        "id": "user_1",
        "name": "Alice Smith",
        "email": "alice@example.com",
        "created_at": "2026-02-27T15:00:00Z"
      },
      {
        "id": "user_2",
        "name": "Bob Jones",
        "email": "bob@example.com",
        "created_at": "2026-02-27T15:05:00Z"
      }
    ]
  }'
```

**Query rows:**
```bash
curl -X POST http://localhost:8000/v1/projects/{project_id}/database/tables/users/query \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "name": {"$contains": "Alice"}
    },
    "limit": 10
  }'
```

### Uploading Files

**Upload a file to object storage:**
```bash
curl -X POST http://localhost:8000/v1/projects/{project_id}/storage/files/upload \
  -F "file=@/path/to/your/file.pdf" \
  -F "metadata={\"category\": \"documents\", \"tags\": [\"important\"]}"
```

**List files:**
```bash
curl http://localhost:8000/v1/projects/{project_id}/storage/files/list
```

**Download a file:**
```bash
curl http://localhost:8000/v1/projects/{project_id}/storage/files/{file_id}/download \
  --output downloaded-file.pdf
```

### Event Streaming

**Create an event:**
```bash
curl -X POST http://localhost:8000/v1/projects/{project_id}/events/create \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "user.created",
    "data": {
      "user_id": "user_1",
      "email": "alice@example.com"
    },
    "timestamp": "2026-02-27T15:00:00Z"
  }'
```

**List events:**
```bash
curl http://localhost:8000/v1/projects/{project_id}/events/list?limit=100
```

## CLI Tool Setup

The ZeroDB CLI provides a convenient interface for managing your local environment and syncing with the cloud.

### Installation

```bash
cd cli
pip install -e .
```

**Verify installation:**
```bash
zerodb --version
```

### Basic Commands

```bash
# Check service status
zerodb local status

# View logs
zerodb local logs

# Stop all services
zerodb local down

# Restart all services
zerodb local restart

# View API documentation
zerodb docs
```

### Cloud Integration (Optional)

```bash
# Login to ZeroDB Cloud
zerodb cloud login

# Link your local project to a cloud project
zerodb cloud link proj_cloud_xyz

# See what changes would be synced
zerodb sync plan

# Sync local changes to cloud
zerodb sync apply

# Pull changes from cloud
zerodb cloud pull
```

For detailed cloud sync configuration, see [Sync Strategy](./SYNC_STRATEGY.md).

## Dashboard Tour

### Projects View
- View all your local projects
- Create new projects
- Delete projects
- See project statistics (vectors, tables, files, events)

### Vectors View
- Browse all vectors in a project
- Search vectors by similarity
- View vector metadata
- Delete vectors
- Export vectors as JSON/CSV

### Tables View
- List all tables in a project
- View table schemas
- Query table data with filters
- Insert, update, delete rows
- Export table data

### Files View
- Browse uploaded files
- Upload new files (drag & drop supported)
- Download files
- View file metadata
- Delete files

### Events View
- Stream of all events in real-time
- Filter events by type
- View event payloads
- Export event logs

### Sync View
- See sync status with cloud
- View pending changes
- Trigger manual sync
- Configure conflict resolution
- View sync history

## Next Steps

Congratulations! You now have ZeroDB Local up and running. Here's what to explore next:

### Learn More

- **[Environment Setup](./ENVIRONMENT_SETUP.md)** - Configure for different environments (development, staging, production)
- **[Data Management](./DATA_MANAGEMENT.md)** - Backups, restores, and data lifecycle management
- **[Troubleshooting](./TROUBLESHOOTING.md)** - Solutions to common issues
- **[Sync Strategy](./SYNC_STRATEGY.md)** - Advanced cloud synchronization patterns

### Try Advanced Features

1. **Semantic Search**: Build a document search system using embeddings
2. **Event Sourcing**: Use RedPanda for event-driven architectures
3. **Hybrid Storage**: Combine vectors, tables, and files in one application
4. **Cloud Sync**: Develop locally, deploy to cloud seamlessly

### Example Applications

Check out the `examples/` directory in the repository for complete applications:

- `examples/document-qa/` - Document Q&A with semantic search
- `examples/event-driven-app/` - Event-sourced application
- `examples/multi-tenant/` - Multi-project architecture
- `examples/cloud-sync/` - Local development with cloud deployment

### Development Mode

For active development with hot reload:

```bash
# API with hot reload
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Dashboard with hot reload
cd dashboard
npm run dev
```

### API Documentation

Explore the full API documentation at:
- **Interactive Docs**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Performance Tuning

For production workloads, see:
- **[Environment Setup](./ENVIRONMENT_SETUP.md#performance-tuning)** - Optimize for your hardware
- **[Data Management](./DATA_MANAGEMENT.md#scaling)** - Handle large datasets efficiently

## Getting Help

If you run into issues:

1. Check the **[Troubleshooting Guide](./TROUBLESHOOTING.md)**
2. Review logs: `docker-compose logs`
3. Open an issue: https://github.com/AINative-Studio/core/issues
4. Join the community: https://www.ainative.studio/community
5. Email support: hello@ainative.studio

## Summary

You've successfully:
- Installed ZeroDB Local with Docker Compose
- Verified all services are running
- Created your first project
- Stored and searched vectors
- Explored the web dashboard
- Set up the CLI tool

ZeroDB Local gives you the full power of ZeroDB Cloud on your local machine - perfect for development, testing, and offline work.

Happy building!
