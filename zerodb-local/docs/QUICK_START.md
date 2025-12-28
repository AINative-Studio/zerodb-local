# Quick Start Guide

Welcome to ZeroDB Local! This guide will walk you through setting up your first local AI database in less than 10 minutes.

## What You'll Build

By the end of this guide, you'll have:
- ✅ A fully functional ZeroDB Local instance running on your machine
- ✅ All 7 services (PostgreSQL, Qdrant, MinIO, RedPanda, Embeddings, API, Dashboard) operational
- ✅ Your first project created with vector storage
- ✅ Semantic search working with locally-generated embeddings

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] **Docker Desktop** 24.0+ installed and running
  - Download: https://docs.docker.com/get-docker/
  - Verify: `docker --version` should show 24.0 or higher
  - Verify: `docker-compose --version` should show 2.20 or higher

- [ ] **System Resources**:
  - Minimum 8GB RAM (16GB recommended)
  - 20GB free disk space
  - 4 CPU cores available

- [ ] **Network**:
  - Ports 3000, 5432, 6333, 8000, 8001, 9000, 9092 available
  - Internet connection (for initial Docker image downloads only)

- [ ] **Git** installed (to clone repository)

## Step 1: Clone the Repository

```bash
# Clone the AINative Studio repository
git clone https://github.com/ainative/core.git

# Navigate to ZeroDB Local directory
cd core/zerodb-local

# Verify you're in the correct directory
ls -la
# You should see: docker-compose.yml, .env.local.example, README.md
```

## Step 2: Configure Environment

```bash
# Copy the environment template
cp .env.local.example .env.local

# (Optional) Edit the environment file
nano .env.local
```

**Default configuration is ready to use!** You only need to edit `.env.local` if you want to:
- Change default passwords (recommended for non-development use)
- Enable cloud sync (requires API key from https://www.ainative.studio/dashboard/api-keys)
- Use a different embeddings model (small/base/large)

**Key variables you might want to change:**

| Variable | Default | Change if... |
|----------|---------|--------------|
| `POSTGRES_PASSWORD` | `localpass` | You're not just developing locally |
| `MINIO_SECRET_KEY` | `minioadmin` | You're not just developing locally |
| `CLOUD_API_KEY` | (empty) | You want to sync with ZeroDB Cloud |
| `EMBEDDINGS_MODEL` | `bge-small-en-v1.5` | You need more accurate embeddings (use base or large) |

## Step 3: Start All Services

```bash
# Start all services in detached mode
docker-compose up -d

# You'll see output like:
# [+] Running 7/7
#  ✔ Container zerodb-postgres     Started
#  ✔ Container zerodb-qdrant       Started
#  ✔ Container zerodb-minio        Started
#  ✔ Container zerodb-redpanda     Started
#  ✔ Container zerodb-embeddings   Started
#  ✔ Container zerodb-api          Started
#  ✔ Container zerodb-dashboard    Started
```

**First-time startup**: Docker will download all necessary images (~2GB). This takes 5-10 minutes depending on your internet connection.

**Subsequent startups**: Services start in ~30 seconds.

## Step 4: Verify Services

### Check Service Status

```bash
docker-compose ps

# Expected output:
# NAME                  STATUS              PORTS
# zerodb-api            Up 30 seconds       0.0.0.0:8000->8000/tcp
# zerodb-dashboard      Up 30 seconds       0.0.0.0:3000->3000/tcp
# zerodb-embeddings     Up 30 seconds       0.0.0.0:8001->8001/tcp
# zerodb-minio          Up 30 seconds       0.0.0.0:9000-9001->9000-9001/tcp
# zerodb-postgres       Up (healthy)        0.0.0.0:5432->5432/tcp
# zerodb-qdrant         Up 30 seconds       0.0.0.0:6333-6334->6333-6334/tcp
# zerodb-redpanda       Up 30 seconds       0.0.0.0:9092->9092/tcp
```

All services should show "Up" status. PostgreSQL should show "(healthy)" after ~10 seconds.

### Check Overall Health

```bash
curl http://localhost:8000/health | jq

# Expected output:
# {
#   "status": "healthy",
#   "timestamp": "2025-12-28T12:00:00Z",
#   "services": {
#     "postgres": { "status": "healthy", "message": "Database connection successful" },
#     "qdrant": { "status": "healthy" },
#     "minio": { "status": "healthy" },
#     "redpanda": { "status": "healthy" },
#     "embeddings": { "status": "healthy", "model_loaded": true }
#   },
#   "summary": {
#     "healthy": 5,
#     "total": 5,
#     "percentage": 100.0
#   }
# }
```

**All services should report "healthy".** If any service is unhealthy, see [Troubleshooting](#troubleshooting) below.

### Check Individual Services

```bash
# Qdrant
curl http://localhost:6333/healthz
# Expected: {"status":"ok"}

# MinIO
curl http://localhost:9000/minio/health/live
# Expected: (empty response = healthy)

# Embeddings
curl http://localhost:8001/health | jq
# Expected: {"status":"healthy","model_loaded":true}
```

## Step 5: Access the Dashboard

Open your browser to: **http://localhost:3000**

You should see the ZeroDB Local dashboard with:
- Welcome screen
- "Create Project" button
- Navigation menu (Projects, Vectors, Tables, Files, Events)

**Dashboard not loading?**
- Check `docker-compose logs zerodb-dashboard`
- Verify port 3000 is not in use: `lsof -i :3000`

## Step 6: Create Your First Project

### Via Dashboard

1. Click "Create Project" button
2. Enter project name: `my-first-project`
3. Enter description: `Testing ZeroDB Local`
4. Click "Create"
5. Note the `project_id` returned (you'll need this for API calls)

### Via API

```bash
curl -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-first-project",
    "description": "Testing ZeroDB Local"
  }' | jq

# Response:
# {
#   "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
#   "name": "my-first-project",
#   "description": "Testing ZeroDB Local",
#   "created_at": "2025-12-28T12:00:00Z"
# }
```

**Save your project_id!** You'll use it for all subsequent API calls.

## Step 7: Generate Your First Embedding

ZeroDB Local includes a local embeddings service that generates vector embeddings WITHOUT any API costs (no OpenAI API key needed).

```bash
# Generate embedding for a text
curl -X POST http://localhost:8001/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["Hello, world! This is my first embedding."],
    "normalize": true
  }' | jq

# Response:
# {
#   "embeddings": [[0.023, -0.041, 0.012, ... (384 values)]],
#   "model": "BAAI/bge-small-en-v1.5",
#   "dimensions": 384,
#   "count": 1
# }
```

## Step 8: Store Your First Vector

Now let's store a document with its embedding in ZeroDB:

```bash
# Replace PROJECT_ID with your project ID from Step 6
PROJECT_ID="your-project-id-here"

curl -X POST http://localhost:8000/v1/projects/${PROJECT_ID}/database/vectors/upsert \
  -H "Content-Type: application/json" \
  -d '{
    "document": "The quick brown fox jumps over the lazy dog",
    "metadata": {
      "source": "quick-start-guide",
      "category": "example"
    },
    "namespace": "default"
  }' | jq

# Response:
# {
#   "vector_id": "vec_abc123...",
#   "document": "The quick brown fox jumps over the lazy dog",
#   "dimensions": 384,
#   "status": "created"
# }
```

**What just happened?**
1. ZeroDB Local sent your document to the embeddings service
2. The embeddings service generated a 384-dimensional vector
3. The vector was stored in both Qdrant (for fast search) and PostgreSQL (for metadata)

## Step 9: Perform Semantic Search

Let's search for documents similar to a query:

```bash
curl -X POST http://localhost:8000/v1/projects/${PROJECT_ID}/database/vectors/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "animals jumping",
    "limit": 5,
    "threshold": 0.5
  }' | jq

# Response:
# {
#   "results": [
#     {
#       "vector_id": "vec_abc123...",
#       "document": "The quick brown fox jumps over the lazy dog",
#       "score": 0.87,
#       "metadata": {
#         "source": "quick-start-guide",
#         "category": "example"
#       }
#     }
#   ],
#   "count": 1,
#   "query_time_ms": 12
# }
```

**Congratulations!** You just performed semantic search using locally-generated embeddings!

## Step 10: Explore the API

ZeroDB Local provides interactive API documentation:

**Visit: http://localhost:8000/docs**

You'll see:
- All 128 available endpoints
- Request/response schemas
- "Try it out" functionality to test endpoints directly

**Key endpoint categories:**
- `/v1/projects/*` - Project management
- `/v1/projects/{id}/database/vectors/*` - Vector operations
- `/v1/projects/{id}/database/memory/*` - Agent memory
- `/v1/projects/{id}/database/tables/*` - NoSQL tables
- `/v1/projects/{id}/database/files/*` - File storage
- `/v1/projects/{id}/database/events/*` - Event streaming

## Next Steps

### 1. Add More Vectors

```bash
# Batch insert multiple documents
curl -X POST http://localhost:8000/v1/projects/${PROJECT_ID}/database/vectors/batch-upsert \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": [
      {
        "document": "Machine learning is a subset of artificial intelligence",
        "metadata": {"topic": "AI"}
      },
      {
        "document": "Python is a popular programming language for data science",
        "metadata": {"topic": "programming"}
      },
      {
        "document": "Docker containers provide isolated environments for applications",
        "metadata": {"topic": "devops"}
      }
    ]
  }' | jq
```

### 2. Create a NoSQL Table

```bash
curl -X POST http://localhost:8000/v1/projects/${PROJECT_ID}/database/tables \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "users",
    "schema": {
      "fields": {
        "name": "string",
        "email": "string",
        "age": "integer",
        "active": "boolean"
      },
      "indexes": ["email"]
    },
    "description": "User data table"
  }' | jq
```

### 3. Upload a File

```bash
# Create a test file
echo "Hello from ZeroDB Local!" > test.txt

# Upload it (base64 encoded)
FILE_CONTENT=$(base64 -i test.txt)

curl -X POST http://localhost:8000/v1/projects/${PROJECT_ID}/database/files/upload \
  -H "Content-Type: application/json" \
  -d "{
    \"file_name\": \"test.txt\",
    \"file_content\": \"${FILE_CONTENT}\",
    \"content_type\": \"text/plain\",
    \"metadata\": {\"source\": \"quick-start\"}
  }" | jq
```

### 4. Create an Event

```bash
curl -X POST http://localhost:8000/v1/projects/${PROJECT_ID}/database/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "user_action",
    "event_data": {
      "action": "completed_quick_start",
      "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
      "user": "developer"
    },
    "source": "quick_start_guide"
  }' | jq
```

### 5. Setup Cloud Sync (Optional)

If you want to sync with ZeroDB Cloud:

1. **Get API Key**: Visit https://www.ainative.studio/dashboard/api-keys
2. **Add to Environment**: Edit `.env.local` and set `CLOUD_API_KEY`
3. **Restart API**: `docker-compose restart zerodb-api`
4. **Configure Sync**: See [SYNC_STRATEGY.md](./SYNC_STRATEGY.md)

### 6. Create Backups

```bash
# Create a backup
./scripts/backup-local.sh

# List backups
ls -lh backups/

# Restore from backup (if needed)
./scripts/restore-local.sh
```

See [DATA_MANAGEMENT.md](./DATA_MANAGEMENT.md) for automated backups and disaster recovery.

### 7. Monitor Performance

```bash
# Check query performance
curl http://localhost:8000/v1/projects/${PROJECT_ID}/stats | jq

# View service metrics
curl http://localhost:8000/metrics

# Check Qdrant collections
curl http://localhost:6333/collections | jq
```

## Troubleshooting

### Services Won't Start

```bash
# Check Docker is running
docker info

# Check for port conflicts
lsof -i :8000 -i :5432 -i :6333 -i :9000

# View logs for specific service
docker-compose logs zerodb-api
docker-compose logs zerodb-postgres
docker-compose logs zerodb-embeddings
```

### Health Check Fails

```bash
# Check which service is unhealthy
curl http://localhost:8000/health | jq '.services'

# Restart unhealthy service
docker-compose restart zerodb-<service-name>

# View service logs
docker-compose logs --tail=50 zerodb-<service-name>
```

### Embeddings Service Slow

```bash
# Check if model is loaded
curl http://localhost:8001/health | jq

# View embeddings service logs
docker-compose logs zerodb-embeddings

# Model download might be in progress (first run)
# Wait 2-3 minutes for download to complete
```

### Can't Connect to Database

```bash
# Check PostgreSQL is healthy
docker-compose exec postgres pg_isready -U zerodb

# Connect manually to verify
docker-compose exec postgres psql -U zerodb -d zerodb_local

# Run SQL query
\dt  # List tables
SELECT COUNT(*) FROM projects;
```

For more detailed troubleshooting, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

## Understanding the Architecture

### Data Flow

```
1. Client Request
   └─> API Server (FastAPI) :8000

2. API Server Processing
   ├─> Generate Embedding
   │   └─> Embeddings Service :8001
   │       └─> BAAI BGE Model (local)
   │
   ├─> Store Vector
   │   ├─> Qdrant :6333 (fast similarity search)
   │   └─> PostgreSQL :5432 (metadata + backup)
   │
   ├─> Store File
   │   └─> MinIO :9000 (S3-compatible storage)
   │
   └─> Emit Event
       └─> RedPanda :9092 (event stream)

3. Client Response
   └─> JSON with results
```

### Service Purposes

- **PostgreSQL**: Relational data, metadata, change logs
- **Qdrant**: High-speed vector similarity search
- **MinIO**: Object storage for files
- **RedPanda**: Event streaming for real-time notifications
- **Embeddings**: Local vector generation (no API costs!)
- **API**: REST interface matching ZeroDB Cloud
- **Dashboard**: Web UI for management

## Key Concepts

### Projects
- Container for all your data (vectors, tables, files, events)
- Each project has a unique ID
- Projects can be linked to ZeroDB Cloud projects

### Vectors
- 384-dimensional embeddings (default model)
- Stored in both Qdrant (search) and PostgreSQL (backup)
- Support metadata filtering and namespaces

### Namespaces
- Logical grouping within a project
- Default namespace: "default"
- Use for multi-tenant or organizational separation

### Metadata
- JSON objects attached to vectors, tables, files
- Fully searchable and filterable
- No schema restrictions

## Additional Resources

- **Environment Setup**: [ENVIRONMENT_SETUP.md](./ENVIRONMENT_SETUP.md)
- **Data Management**: [DATA_MANAGEMENT.md](./DATA_MANAGEMENT.md)
- **Sync Strategy**: [SYNC_STRATEGY.md](./SYNC_STRATEGY.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- **API Docs**: http://localhost:8000/docs
- **Community**: https://www.ainative.studio/community

## Getting Help

- **GitHub Issues**: https://github.com/ainative/core/issues
- **Documentation**: https://www.ainative.studio/docs
- **Email Support**: hello@ainative.studio
- **Community Forum**: https://www.ainative.studio/community

---

**Congratulations!** You've successfully set up ZeroDB Local and performed your first semantic search with locally-generated embeddings.

**What's next?**
- Build an AI agent with persistent memory
- Create a RAG (Retrieval Augmented Generation) system
- Build a semantic search engine for your documents
- Deploy a privacy-first AI application

Welcome to the world of self-hosted AI infrastructure! 🚀
