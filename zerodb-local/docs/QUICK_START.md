# Quick Start Guide - ZeroDB Local

**Complete guide to getting started with ZeroDB Local CLI and services in under 10 minutes.**

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation)
3. [Starting ZeroDB Local](#3-starting-zerodb-local)
4. [Accessing Services](#4-accessing-services)
5. [Using the CLI](#5-using-the-cli)
   - [5.1 Local Environment Commands (7)](#51-local-environment-commands-7-commands)
   - [5.2 Sync with Cloud (2)](#52-sync-with-cloud-2-commands)
   - [5.3 Inspect Database (7)](#53-inspect-database-7-commands)
6. [Common Workflows](#6-common-workflows)
7. [Troubleshooting](#7-troubleshooting)
8. [Next Steps](#8-next-steps)

---

## 1. Prerequisites

Before starting, ensure you have:

### Docker Environment
- **Docker Desktop** 20.10+ installed and running
- **Docker Compose** 2.0+ (usually bundled with Docker Desktop)
- Verify installation:
  ```bash
  docker --version
  # Expected: Docker version 20.10.0 or higher

  docker compose version
  # Expected: Docker Compose version v2.0.0 or higher
  ```

### System Resources
- **RAM**: At least 4GB available (8GB recommended)
- **Disk Space**: 10GB free (for Docker images and data)
- **CPU**: 2 cores minimum (4 cores recommended)
- **Ports Available**: 3000, 5432, 6333, 8000, 8001, 9000, 9092

### Python Environment (for CLI)
- **Python 3.11+** installed
- **pip** package manager
- Verify installation:
  ```bash
  python3 --version
  # Expected: Python 3.11.0 or higher

  pip3 --version
  # Expected: pip 23.0 or higher
  ```

### Network
- Internet connection (for initial Docker image downloads only)
- No corporate proxy restrictions on Docker Hub

---

## 2. Installation

### Step 2.1: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/ainative/core.git

# Navigate to ZeroDB Local directory
cd core/zerodb-local

# Verify you're in the correct directory
ls -la
# You should see: docker-compose.yml, .env.local.example, cli/
```

### Step 2.2: Install the CLI

```bash
# Navigate to CLI directory
cd cli

# Install CLI in editable mode
pip install -e .

# Verify installation
zerodb --version
# Expected: ZeroDB CLI version 1.0.0

# View available commands
zerodb --help
```

**Expected output:**
```
Usage: zerodb [OPTIONS] COMMAND [ARGS]...

  ZeroDB Local CLI - Manage your local AI database

Commands:
  local    Manage local Docker services
  sync     Synchronize with ZeroDB Cloud
  inspect  Inspect database state and health
```

### Step 2.3: Navigate Back to Root

```bash
# Return to zerodb-local root directory
cd ..

# Verify location
pwd
# Expected: /path/to/core/zerodb-local
```

---

## 3. Starting ZeroDB Local

### Step 3.1: Initialize Environment (First Time Only)

```bash
# Initialize local environment
zerodb local init

# This will:
# - Create .env.local from .env.local.example
# - Generate secure random passwords
# - Set default configuration
```

**Expected output:**
```
✓ Created .env.local from template
✓ Generated secure passwords
✓ Configuration ready

Next step: zerodb local up
```

### Step 3.2: Start All Services

```bash
# Start all services in detached mode
zerodb local up

# Equivalent to: docker compose up -d
```

**Expected output:**
```
Starting ZeroDB Local services...
[+] Running 7/7
 ✔ Container zerodb-postgres     Started
 ✔ Container zerodb-qdrant       Started
 ✔ Container zerodb-minio        Started
 ✔ Container zerodb-redpanda     Started
 ✔ Container zerodb-embeddings   Started
 ✔ Container zerodb-api          Started
 ✔ Container zerodb-dashboard    Started

All services started successfully!
Dashboard: http://localhost:3000
API Docs: http://localhost:8000/docs
```

**First-time startup:** Docker will download images (~2GB). This takes 5-10 minutes.

**Subsequent startups:** Services start in ~30 seconds.

### Step 3.3: Check System Health

```bash
# Check health of all services
zerodb inspect health

# This will test:
# - PostgreSQL connection
# - Qdrant vector store
# - MinIO object storage
# - RedPanda event stream
# - Embeddings service
# - API server
```

**Expected output:**
```
┌─────────────────────────────────────────────────┐
│             ZeroDB Health Status                │
├─────────────────────────────────────────────────┤
│ Overall Status: HEALTHY                         │
│ Timestamp: 2025-12-29T12:00:00Z                 │
├─────────────────────────────────────────────────┤
│ Service Health:                                 │
│  ✓ PostgreSQL: healthy (10ms)                   │
│  ✓ Qdrant: healthy                              │
│  ✓ MinIO: healthy                               │
│  ✓ RedPanda: healthy                            │
│  ✓ Embeddings: healthy (model loaded)           │
│  ✓ API: healthy                                 │
├─────────────────────────────────────────────────┤
│ Summary: 6/6 services healthy (100%)            │
└─────────────────────────────────────────────────┘
```

### Step 3.4: View Service Status

```bash
# View detailed service status
zerodb local status

# Shows Docker container status
```

**Expected output:**
```
┌──────────────────────────┬─────────┬────────────────────────┐
│ Service                  │ Status  │ Ports                  │
├──────────────────────────┼─────────┼────────────────────────┤
│ zerodb-postgres          │ Up      │ 0.0.0.0:5432->5432/tcp │
│ zerodb-qdrant            │ Up      │ 0.0.0.0:6333->6333/tcp │
│ zerodb-minio             │ Up      │ 0.0.0.0:9000->9000/tcp │
│ zerodb-redpanda          │ Up      │ 0.0.0.0:9092->9092/tcp │
│ zerodb-embeddings        │ Up      │ 0.0.0.0:8001->8001/tcp │
│ zerodb-api               │ Up      │ 0.0.0.0:8000->8000/tcp │
│ zerodb-dashboard         │ Up      │ 0.0.0.0:3000->3000/tcp │
└──────────────────────────┴─────────┴────────────────────────┘
```

---

## 4. Accessing Services

Once all services are running, you can access them at the following URLs:

### Web Interfaces

| Service | URL | Description |
|---------|-----|-------------|
| **API Documentation** | http://localhost:8000/docs | Interactive OpenAPI/Swagger documentation |
| **Dashboard** | http://localhost:3000 | ZeroDB web dashboard (coming soon) |
| **Qdrant Dashboard** | http://localhost:6333/dashboard | Vector database web UI |
| **MinIO Console** | http://localhost:9001 | Object storage web console |

### API Endpoints

| Endpoint | URL | Authentication |
|----------|-----|----------------|
| **API Base** | http://localhost:8000/v1 | API Key or JWT |
| **Health Check** | http://localhost:8000/health | None |
| **Embeddings** | http://localhost:8001 | Internal only |

### Database Connections

| Service | Connection | Credentials |
|---------|-----------|-------------|
| **PostgreSQL** | `postgresql://localhost:5432/zerodb_local` | User: `zerodb`, Password: in `.env.local` |
| **Qdrant** | `http://localhost:6333` | No authentication in local mode |
| **MinIO** | `http://localhost:9000` | Access key/secret in `.env.local` |
| **RedPanda** | `localhost:9092` | No authentication in local mode |

---

## 5. Using the CLI

The ZeroDB CLI provides three main command groups with 21 total commands:

### 5.1 Local Environment Commands (7 commands)

Manage Docker services and local environment.

#### `zerodb local init` - Initialize Environment

```bash
# Initialize data directories and configuration (first-time only)
zerodb local init

# This will:
# - Create .env.local from template
# - Generate secure passwords
# - Set default configuration
# - Prepare data directories
```

#### `zerodb local up` - Start Services

```bash
# Start all services
zerodb local up

# Start in foreground (see logs)
zerodb local up --foreground

# Start specific service
zerodb local up --service zerodb-api
```

#### `zerodb local down` - Stop Services

```bash
# Stop all services (preserves data)
zerodb local down

# Stop and remove volumes (deletes data!)
zerodb local down --volumes
```

#### `zerodb local status` - Service Status

```bash
# View detailed service status
zerodb local status

# Shows Docker container status, health, and ports
```

#### `zerodb local logs` - View Logs

```bash
# View logs from all services
zerodb local logs

# Follow logs in real-time
zerodb local logs --follow

# View logs for specific service
zerodb local logs zerodb-api

# View last 50 lines
zerodb local logs --tail 50 zerodb-api
```

#### `zerodb local restart` - Restart Services

```bash
# Restart all services
zerodb local restart

# Restart specific service
zerodb local restart --service zerodb-api
```

#### `zerodb local reset` - Full Reset

```bash
# Stop and remove everything (fresh start)
zerodb local reset

# Confirm with --yes flag
zerodb local reset --yes

# This will:
# - Stop all containers
# - Remove all volumes (DATA LOSS!)
# - Clean up networks
# - Reset to initial state
```

**⚠️ WARNING:** `reset` command deletes ALL local data. Backup first!

---

### 5.2 Sync with Cloud (2 commands)

Synchronize data between local and ZeroDB Cloud.

#### `zerodb sync plan` - Plan Sync (Preview Changes)

```bash
# Plan pull from cloud (preview only, default)
zerodb sync plan

# Plan push to cloud
zerodb sync plan --direction push

# Plan bidirectional sync
zerodb sync plan --direction bidirectional

# Dry run (no changes, test connection)
zerodb sync plan --dry-run

# JSON output for scripting
zerodb sync plan --output json
```

**Expected output:**
```
┌─────────────────────────────────────────────────┐
│           Sync Plan Summary                     │
├─────────────────────────────────────────────────┤
│ Direction: cloud → local (pull)                 │
│ Mode: Preview (no changes will be made)         │
├─────────────────────────────────────────────────┤
│ Changes to apply:                               │
│  - CREATE: 5 vectors                            │
│  - UPDATE: 2 vectors                            │
│  - DELETE: 0 vectors                            │
│  - CREATE: 1 table                              │
│  - SKIP: 3 unchanged                            │
├─────────────────────────────────────────────────┤
│ Conflicts detected: 1                           │
│  - Vector vec_abc123: Modified locally and in   │
│    cloud. Strategy: cloud_wins (cloud version   │
│    will be used)                                │
├─────────────────────────────────────────────────┤
│ Estimated time: ~10 seconds                     │
│ Data transfer: ~2.5 MB                          │
└─────────────────────────────────────────────────┘

To apply this plan: zerodb sync apply
```

#### `zerodb sync apply` - Execute Sync

```bash
# Execute pull from cloud (interactive, default)
zerodb sync apply

# Execute push to cloud
zerodb sync apply --direction push

# Execute bidirectional sync
zerodb sync apply --direction bidirectional

# Auto-approve (skip confirmation)
zerodb sync apply --auto-approve

# Combined: auto-approve push
zerodb sync apply --direction push --auto-approve

# Force sync (ignore conflicts, use cloud version)
zerodb sync apply --force
```

**Interactive prompts:**
```
Sync Plan Review:
- 5 vectors to create
- 2 vectors to update
- 1 table to create

Apply these changes? [y/N]: y

Executing sync...
 ✓ Created vector vec_001 (1/5)
 ✓ Created vector vec_002 (2/5)
 ✓ Created vector vec_003 (3/5)
 ✓ Created vector vec_004 (4/5)
 ✓ Created vector vec_005 (5/5)
 ✓ Updated vector vec_abc (1/2)
 ✓ Updated vector vec_def (2/2)
 ✓ Created table users (1/1)

Sync completed successfully!
- Duration: 12 seconds
- Items synced: 8
- Errors: 0
```

---

### 5.3 Inspect Database (7 commands)

View database state, health, and statistics.

#### `zerodb inspect health` - Check System Health

```bash
# Check health of all services
zerodb inspect health

# JSON output
zerodb inspect health --json

# Include detailed diagnostics
zerodb inspect health --verbose
```

#### `zerodb inspect projects` - List Projects

```bash
# List all local projects
zerodb inspect projects

# Include vector counts and details
zerodb inspect projects --details

# JSON output for scripting
zerodb inspect projects --json
```

**Expected output:**
```
┌───────────────────────────────────────────────────────────────┐
│                     Local Projects                            │
├───────────────────────────────────────────────────────────────┤
│ ID: proj_abc123                                               │
│ Name: my-first-project                                        │
│ Description: Testing ZeroDB Local                             │
│ Created: 2025-12-29T10:00:00Z                                 │
│ Vectors: 127                                                  │
│ Tables: 3                                                     │
│ Files: 5                                                      │
├───────────────────────────────────────────────────────────────┤
│ ID: proj_def456                                               │
│ Name: ai-agent-memory                                         │
│ Description: Memory store for AI agents                       │
│ Created: 2025-12-28T15:30:00Z                                 │
│ Vectors: 342                                                  │
│ Tables: 1                                                     │
│ Files: 0                                                      │
└───────────────────────────────────────────────────────────────┘

Total projects: 2
```

#### `zerodb inspect sync` - View Sync State

```bash
# Check sync status with cloud
zerodb inspect sync

# Show last sync time and history
zerodb inspect sync --history

# Show pending changes (items to sync)
zerodb inspect sync --pending

# JSON output
zerodb inspect sync --json
```

**Expected output:**
```
┌─────────────────────────────────────────────────┐
│            Sync Status                          │
├─────────────────────────────────────────────────┤
│ Cloud Connection: Connected                     │
│ Last Sync: 2025-12-29T11:45:00Z (15m ago)       │
│ Direction: bidirectional                        │
├─────────────────────────────────────────────────┤
│ Local Changes (pending push):                   │
│  - 3 new vectors                                │
│  - 1 updated vector                             │
│  - 0 deletions                                  │
├─────────────────────────────────────────────────┤
│ Cloud Changes (pending pull):                   │
│  - 5 new vectors                                │
│  - 2 updated vectors                            │
│  - 1 deletion                                   │
├─────────────────────────────────────────────────┤
│ Conflicts: 0                                    │
│ Auto-sync: disabled                             │
└─────────────────────────────────────────────────┘

Run 'zerodb sync plan' to preview changes
```

#### `zerodb inspect vectors` - Vector Statistics

```bash
# Get vector statistics for all namespaces
zerodb inspect vectors

# Filter by specific namespace
zerodb inspect vectors --namespace default

# Include embedding model info and details
zerodb inspect vectors --verbose

# JSON output
zerodb inspect vectors --json
```

#### `zerodb inspect tables` - Table Information

```bash
# List all NoSQL tables
zerodb inspect tables

# Show table schemas
zerodb inspect tables --schemas

# Count rows in tables
zerodb inspect tables --counts

# Combined: schemas and counts
zerodb inspect tables --schemas --counts

# JSON output
zerodb inspect tables --json
```

#### `zerodb inspect files` - File Storage

```bash
# List files in storage
zerodb inspect files

# Filter by folder/path
zerodb inspect files --folder /uploads

# Show file sizes and metadata
zerodb inspect files --details

# JSON output
zerodb inspect files --json
```

#### `zerodb inspect events` - Event Stream

```bash
# List recent events
zerodb inspect events

# Filter by event type
zerodb inspect events --type vector.created

# Show events from specific time range
zerodb inspect events --since 2025-12-29

# Limit number of events
zerodb inspect events --limit 100

# JSON output
zerodb inspect events --json
```

---

## 6. Common Workflows

### 6.1 First-Time Setup

Complete workflow for new users:

```bash
# 1. Initialize environment
zerodb local init

# 2. Start all services
zerodb local up

# 3. Wait for services to be ready (30 seconds)
sleep 30

# 4. Check health
zerodb inspect health

# 5. View dashboard
open http://localhost:3000

# 6. View API documentation
open http://localhost:8000/docs
```

### 6.2 Daily Development Workflow

Typical workflow for daily development:

```bash
# Morning: Start services
zerodb local up

# Check everything is healthy
zerodb inspect health

# View your projects
zerodb inspect projects

# ... do your development work ...

# Afternoon: Sync progress to cloud
zerodb sync plan --direction push
zerodb sync apply --auto-approve

# Evening: Stop services (preserves data)
zerodb local down
```

### 6.3 Sync Workflow

Best practices for synchronization:

```bash
# 1. Always plan first
zerodb sync plan

# 2. Review the plan carefully
# Look for conflicts and unexpected changes

# 3. If plan looks good, apply it
zerodb sync apply

# 4. Verify sync completed
zerodb inspect sync

# 5. Check your data
zerodb inspect projects --details
```

### 6.4 Troubleshooting Workflow

When things go wrong:

```bash
# 1. Check overall health
zerodb inspect health

# 2. View service logs
zerodb local logs --tail 100

# 3. Check specific service
zerodb local logs zerodb-api --follow

# 4. Restart problematic service
zerodb local restart --service zerodb-api

# 5. If still broken, full restart
zerodb local down
zerodb local up

# 6. Last resort: complete reset (DELETES DATA!)
zerodb local reset
zerodb local init
zerodb local up
```

### 6.5 Backup and Restore Workflow

Regular backup workflow:

```bash
# 1. Create backup before sync
./scripts/backup-local.sh

# 2. Perform sync
zerodb sync apply

# 3. If sync went wrong, restore backup
./scripts/restore-local.sh

# 4. Verify restoration
zerodb inspect projects
```

---

## 7. Troubleshooting

### Issue: Services Won't Start

**Symptoms:**
- `zerodb local up` fails
- Containers exit immediately
- Port binding errors

**Solutions:**

```bash
# Check if Docker is running
docker info

# Check for port conflicts
lsof -i :8000 -i :5432 -i :6333 -i :9000

# View detailed error logs
zerodb local logs

# Try fresh start
zerodb local down
zerodb local up
```

**If ports are in use:**
- Stop conflicting services
- Or edit `.env.local` to change ports

---

### Issue: Sync Fails

**Symptoms:**
- `zerodb sync apply` returns errors
- Connection timeout errors
- Authentication failures

**Solutions:**

```bash
# Check cloud connectivity
curl https://api.ainative.studio/health

# Verify API key in .env.local
cat .env.local | grep CLOUD_API_KEY

# Check sync state
zerodb inspect sync

# Try planning first
zerodb sync plan --dry-run

# If persistent, force sync
zerodb sync apply --force
```

---

### Issue: API Not Responding

**Symptoms:**
- Dashboard won't load
- API requests timeout
- Health check fails

**Solutions:**

```bash
# Check API logs
zerodb local logs zerodb-api --tail 100

# Check if API container is running
docker ps | grep zerodb-api

# Restart API service
zerodb local restart --service zerodb-api

# Test API directly
curl http://localhost:8000/health

# Check PostgreSQL connection
docker exec zerodb-postgres pg_isready -U zerodb
```

---

### Issue: Embeddings Service Slow

**Symptoms:**
- Vector operations timeout
- Model loading errors
- 500 errors on /embeddings

**Solutions:**

```bash
# Check embeddings service
curl http://localhost:8001/health

# View embeddings logs
zerodb local logs zerodb-embeddings --follow

# Model might be downloading (first run)
# Wait 2-3 minutes for download

# Check available memory
docker stats zerodb-embeddings

# Restart embeddings service
zerodb local restart --service zerodb-embeddings
```

---

### Issue: Health Check Shows Unhealthy Services

**Symptoms:**
- `zerodb inspect health` shows failures
- Some services marked as unhealthy

**Solutions:**

```bash
# Identify unhealthy service
zerodb inspect health --verbose

# Check logs for that service
zerodb local logs <service-name> --tail 50

# Try restarting just that service
zerodb local restart --service <service-name>

# If still failing, full restart
zerodb local down
zerodb local up

# Check health again
zerodb inspect health
```

---

### Issue: Complete System Reset Needed

**When everything is broken and you need a fresh start:**

```bash
# CAUTION: This deletes ALL local data!

# 1. Backup if possible
./scripts/backup-local.sh

# 2. Complete reset
zerodb local reset

# 3. Re-initialize
zerodb local init

# 4. Start fresh
zerodb local up

# 5. Verify health
zerodb inspect health

# 6. Restore backup if needed
./scripts/restore-local.sh
```

---

## 8. Next Steps

### Explore the API

```bash
# Open interactive API documentation
open http://localhost:8000/docs

# Try creating a project via API
curl -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "test-project", "description": "Testing API"}' | jq
```

### Set Up Cloud Sync

```bash
# 1. Get API key from dashboard
open https://www.ainative.studio/dashboard/api-keys

# 2. Add to .env.local
echo 'CLOUD_API_KEY=your-api-key-here' >> .env.local

# 3. Restart API
zerodb local restart --service zerodb-api

# 4. Test sync
zerodb sync plan
```

### Build Your First AI Application

```bash
# Example scripts in docs/examples/
ls docs/examples/

# Run first sync example
bash docs/examples/first-sync.sh

# Run daily workflow
bash docs/examples/daily-workflow.sh
```

### Explore Example Scripts

Run example scripts to automate common workflows:

```bash
# First-time setup automation
bash docs/examples/first-time-setup.sh

# Daily development workflow
bash docs/examples/daily-workflow.sh

# Comprehensive system inspection
bash docs/examples/inspect-all.sh

# First sync with cloud
bash docs/examples/first-sync.sh

# Backup and restore
bash docs/examples/backup-restore.sh
```

**Available Example Scripts:**
- `first-time-setup.sh` - Complete first-time installation and verification
- `daily-workflow.sh` - Morning to evening development workflow
- `inspect-all.sh` - Comprehensive database inspection
- `first-sync.sh` - First sync with cloud walkthrough
- `backup-restore.sh` - Backup and restore operations

### Read More Documentation

- **CLI Reference**: `docs/cli/` - Complete CLI documentation
- **API Documentation**: http://localhost:8000/docs
- **Sync Architecture**: `docs/SYNC_ARCHITECTURE_DIAGRAM.md`
- **Data Management**: `docs/DATA_MANAGEMENT.md`
- **Environment Setup**: `docs/ENVIRONMENT_SETUP.md`
- **Troubleshooting**: `docs/TROUBLESHOOTING.md`

### Join the Community

- **GitHub**: https://github.com/ainative/core
- **Documentation**: https://www.ainative.studio/docs
- **Community Forum**: https://www.ainative.studio/community
- **Support**: hello@ainative.studio

---

**Congratulations!** You now have a complete understanding of the ZeroDB Local CLI and workflows.

**What's next?**
- Build an AI agent with persistent memory
- Create a RAG (Retrieval Augmented Generation) system
- Build a semantic search engine
- Deploy a privacy-first AI application

Welcome to self-hosted AI infrastructure! 🚀

---

**Last Updated:** 2025-12-29
**ZeroDB Local:** v1.0.0
**Epic 3:** CLI Tool - COMPLETE
**Total Commands:** 21 (7 local + 2 sync + 7 inspect + 5 utility)
