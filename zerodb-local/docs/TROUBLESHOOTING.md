# ZeroDB Local - Troubleshooting Guide

Comprehensive troubleshooting guide for common issues with ZeroDB Local. Solutions organized by service and symptom.

## Table of Contents

- [General Troubleshooting Steps](#general-troubleshooting-steps)
- [Services Won't Start](#services-wont-start)
- [Port Conflicts](#port-conflicts)
- [Database Issues](#database-issues)
- [Vector Search Issues](#vector-search-issues)
- [Object Storage Issues](#object-storage-issues)
- [Event Streaming Issues](#event-streaming-issues)
- [Embeddings Service Issues](#embeddings-service-issues)
- [API Server Issues](#api-server-issues)
- [Dashboard Issues](#dashboard-issues)
- [Performance Issues](#performance-issues)
- [Cloud Sync Issues](#cloud-sync-issues)
- [Docker Issues](#docker-issues)
- [Network Issues](#network-issues)
- [Data Corruption](#data-corruption)

## General Troubleshooting Steps

Before diving into specific issues, try these general steps:

### 1. Check Service Status

```bash
# View all services
docker-compose ps

# View logs for all services
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View logs for specific service
docker-compose logs postgres
docker-compose logs api
docker-compose logs qdrant
```

### 2. Restart Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart api
docker-compose restart postgres
```

### 3. Full Reset (Nuclear Option)

When all else fails:

```bash
# Stop and remove everything
docker-compose down -v

# Remove data (WARNING: Data loss!)
rm -rf data/

# Start fresh
docker-compose up -d
```

### 4. Check System Resources

```bash
# Check disk space
df -h

# Check memory usage
free -h  # Linux
vm_stat  # macOS

# Check CPU usage
top

# Check Docker resources
docker stats
```

### 5. Verify Environment Configuration

```bash
# Check environment file exists
ls -la .env.local

# Validate Docker Compose config
docker-compose config

# Check for syntax errors
docker-compose config --quiet && echo "Config OK" || echo "Config has errors"
```

## Services Won't Start

### Symptom: Services Keep Restarting

**Check logs:**
```bash
docker-compose logs --tail=100
```

**Common causes:**

#### 1. Port Already in Use

```bash
# Check which ports are in use
lsof -i :5432 -i :6333 -i :8000 -i :9000

# Kill process using port
kill -9 $(lsof -t -i :8000)

# Or change ports in docker-compose.yml
```

#### 2. Insufficient Memory

```bash
# Check Docker memory limit
docker info | grep -i memory

# Increase Docker memory (Docker Desktop settings)
# Preferences > Resources > Memory > 8GB

# Or reduce service resource requirements in docker-compose.yml
```

#### 3. Permission Issues

```bash
# Fix data directory permissions
sudo chown -R $USER:$USER data/

# Make data directories writable
chmod -R 755 data/
```

### Symptom: Container Exits Immediately

**View exit code:**
```bash
docker-compose ps
```

**Common exit codes:**

| Exit Code | Meaning | Solution |
|-----------|---------|----------|
| 0 | Normal exit | Service completed (not expected for long-running services) |
| 1 | Application error | Check logs for error message |
| 126 | Permission denied | Fix file permissions |
| 127 | Command not found | Check Docker image |
| 137 | Out of memory | Increase Docker memory limit |
| 139 | Segmentation fault | Report bug, try different version |

**Check container logs:**
```bash
docker-compose logs postgres
```

### Symptom: Services Not Healthy

**Check health status:**
```bash
docker-compose ps

# Should show "(healthy)" for most services
```

**Test health endpoints manually:**
```bash
# API
curl http://localhost:8000/health

# Embeddings
curl http://localhost:8001/health

# Qdrant
curl http://localhost:6333/

# MinIO
curl http://localhost:9000/minio/health/live
```

## Port Conflicts

### Symptom: "Address already in use"

**Error message:**
```
Error starting userland proxy: listen tcp4 0.0.0.0:8000: bind: address already in use
```

**Solution 1: Find and Kill Conflicting Process**

```bash
# macOS/Linux
lsof -i :8000
kill -9 <PID>

# Windows (PowerShell)
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Solution 2: Change Ports in docker-compose.yml**

```yaml
services:
  api:
    ports:
      - "8080:8000"  # Use 8080 instead of 8000
```

**Solution 3: Stop Conflicting Docker Containers**

```bash
# List all running containers
docker ps

# Stop specific container
docker stop <container_name>

# Stop all containers
docker stop $(docker ps -q)
```

## Database Issues

### Symptom: "Connection refused" to PostgreSQL

**Check PostgreSQL is running:**
```bash
docker-compose ps postgres

# Should show "Up" status
```

**Test connection:**
```bash
# From host
docker-compose exec postgres pg_isready -U zerodb -d zerodb_local

# Expected: "accepting connections"
```

**Check logs:**
```bash
docker-compose logs postgres | tail -50
```

**Common causes:**

#### 1. PostgreSQL Still Starting

Wait 30 seconds and retry. First startup takes longer.

#### 2. Wrong Credentials

Check `.env.local`:
```env
POSTGRES_USER=zerodb
POSTGRES_PASSWORD=localpass
POSTGRES_DB=zerodb_local
```

#### 3. Data Directory Corruption

```bash
# Stop PostgreSQL
docker-compose stop postgres

# Move corrupted data
mv data/postgres data/postgres.backup

# Create fresh database
docker-compose up -d postgres

# Restore from backup (if available)
# See Data Management guide
```

### Symptom: "QueuePool limit reached"

**Error message:**
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 10 overflow 10 reached
```

**Solution 1: Close Idle Connections**

```bash
# Kill idle connections
docker-compose exec postgres psql -U zerodb -d zerodb_local -c "
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE datname = 'zerodb_local'
    AND pid <> pg_backend_pid()
    AND state = 'idle'
    AND state_change < current_timestamp - INTERVAL '5 minutes';
"
```

**Solution 2: Increase Pool Size**

Edit `.env.local`:
```env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=20
```

Restart API:
```bash
docker-compose restart api
```

**Solution 3: Stop Development Servers**

If running multiple dev servers:
```bash
# Stop all Python processes
pkill -f "uvicorn"
pkill -f "python.*main.py"

# Wait 30 seconds for connections to close
sleep 30

# Restart
docker-compose restart api
```

### Symptom: Slow Queries

**Check active queries:**
```bash
docker-compose exec postgres psql -U zerodb -d zerodb_local -c "
  SELECT
    pid,
    now() - query_start AS duration,
    query,
    state
  FROM pg_stat_activity
  WHERE state != 'idle'
  ORDER BY duration DESC;
"
```

**Solution: Add Indexes**

```bash
docker-compose exec postgres psql -U zerodb -d zerodb_local -c "
  CREATE INDEX idx_vectors_created_at ON vectors(created_at);
  CREATE INDEX idx_vectors_metadata ON vectors USING GIN(metadata);
"
```

**Solution: Vacuum Database**

```bash
docker-compose exec postgres psql -U zerodb -d zerodb_local -c "VACUUM ANALYZE;"
```

## Vector Search Issues

### Symptom: Qdrant Not Responding

**Test connection:**
```bash
curl http://localhost:6333/
```

**Check health:**
```bash
curl http://localhost:6333/healthz
```

**Check logs:**
```bash
docker-compose logs qdrant | tail -50
```

**Solution: Restart Qdrant**

```bash
docker-compose restart qdrant
```

### Symptom: Search Results Empty or Irrelevant

**Common causes:**

#### 1. Wrong Vector Dimensions

```bash
# Check collection config
curl http://localhost:6333/collections/{collection_name}

# Verify dimensions match embedding model
# BAAI/bge-small-en-v1.5 = 384 dimensions
# BAAI/bge-base-en-v1.5 = 768 dimensions
# BAAI/bge-large-en-v1.5 = 1024 dimensions
```

#### 2. Threshold Too High

```bash
# Lower similarity threshold
curl -X POST http://localhost:8000/v1/projects/{project_id}/database/vectors/search \
  -d '{
    "query_vector": [...],
    "threshold": 0.5  # Lower from 0.7 to 0.5
  }'
```

#### 3. Empty Collection

```bash
# Check vector count
curl http://localhost:6333/collections/{collection_name}

# Look for "points_count" in response
```

### Symptom: Qdrant Out of Memory

**Error in logs:**
```
allocation of X bytes failed
```

**Solution 1: Enable Quantization**

```bash
# Reduce memory usage with scalar quantization
curl -X PUT http://localhost:6333/collections/{collection_name}/quantization \
  -H "Content-Type: application/json" \
  -d '{
    "scalar": {
      "type": "int8",
      "quantile": 0.99
    }
  }'
```

**Solution 2: Increase Docker Memory**

```bash
# In Docker Desktop: Preferences > Resources > Memory > 8GB+
```

**Solution 3: Use Disk Storage**

```yaml
# docker-compose.yml
services:
  qdrant:
    environment:
      QDRANT__STORAGE__PERFORMANCE__OPTIMIZERS__MEMMAP_THRESHOLD: 10000
```

## Object Storage Issues

### Symptom: MinIO Not Accessible

**Test connection:**
```bash
curl http://localhost:9000/minio/health/live
```

**Check logs:**
```bash
docker-compose logs minio | tail -50
```

**Common causes:**

#### 1. Wrong Credentials

Check `.env.local`:
```env
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
```

#### 2. Bucket Doesn't Exist

```bash
# Install MinIO client
brew install minio/stable/mc

# Configure
mc alias set local http://localhost:9000 minioadmin minioadmin

# Create bucket
mc mb local/zerodb-local

# List buckets
mc ls local/
```

### Symptom: File Upload Fails

**Error: "Access Denied"**

```bash
# Check bucket policy
mc policy get local/zerodb-local

# Set public policy (for testing only!)
mc policy set download local/zerodb-local

# Set private policy (production)
mc policy set private local/zerodb-local
```

**Error: "File too large"**

Check API limits in `.env.local`:
```env
MAX_UPLOAD_SIZE_MB=100  # Increase if needed
```

## Event Streaming Issues

### Symptom: RedPanda Not Responding

**Check status:**
```bash
docker-compose logs redpanda | tail -50
```

**Test connection:**
```bash
docker-compose exec redpanda rpk cluster info
```

**Solution: Restart RedPanda**

```bash
docker-compose restart redpanda
```

### Symptom: Events Not Being Consumed

**List topics:**
```bash
docker-compose exec redpanda rpk topic list
```

**Check topic lag:**
```bash
docker-compose exec redpanda rpk group describe {consumer_group}
```

**Reset consumer offset:**
```bash
docker-compose exec redpanda rpk group seek {consumer_group} \
  --to start \
  --topics {topic_name}
```

## Embeddings Service Issues

### Symptom: Embeddings Service Slow or Timing Out

**Check logs:**
```bash
docker-compose logs embeddings | tail -50
```

**Common causes:**

#### 1. Model Downloading (First Start)

Wait 5-10 minutes for model download to complete.

**Check download progress:**
```bash
docker-compose logs -f embeddings
```

#### 2. CPU Bottleneck

**Solution: Use GPU**

```env
# .env.local
EMBEDDINGS_DEVICE=cuda  # NVIDIA GPU
# or
EMBEDDINGS_DEVICE=mps   # Apple Silicon
```

**Restart:**
```bash
docker-compose restart embeddings
```

#### 3. Batch Size Too Large

```env
# .env.local
EMBEDDINGS_BATCH_SIZE=16  # Reduce from 32
```

### Symptom: "CUDA out of memory"

**Error in logs:**
```
RuntimeError: CUDA out of memory
```

**Solution 1: Reduce Batch Size**

```env
EMBEDDINGS_BATCH_SIZE=8
```

**Solution 2: Use Smaller Model**

```env
EMBEDDINGS_MODEL=BAAI/bge-small-en-v1.5  # Instead of large
```

**Solution 3: Fall Back to CPU**

```env
EMBEDDINGS_DEVICE=cpu
```

### Symptom: "Model not found"

**Solution: Clear Model Cache**

```bash
# Stop service
docker-compose stop embeddings

# Clear cache
rm -rf data/embeddings/models/*

# Restart (will re-download)
docker-compose up -d embeddings
```

## API Server Issues

### Symptom: 500 Internal Server Error

**Check API logs:**
```bash
docker-compose logs api | tail -100
```

**Enable debug mode:**

Edit `.env.local`:
```env
DEBUG=true
LOG_LEVEL=debug
```

Restart:
```bash
docker-compose restart api
```

**Common causes:**

#### 1. Database Connection Issue

See [Database Issues](#database-issues)

#### 2. Missing Environment Variables

```bash
docker-compose config | grep -i "missing"
```

#### 3. Python Exception

Check logs for traceback, fix code, rebuild:
```bash
docker-compose build api
docker-compose up -d api
```

### Symptom: API Endpoint Returns 404

**Check route exists:**
```bash
# View OpenAPI docs
open http://localhost:8000/docs

# Or list all routes
curl http://localhost:8000/openapi.json | jq '.paths | keys'
```

**Common cause: Trailing Slash**

Try both with and without trailing slash:
```bash
curl http://localhost:8000/v1/projects
curl http://localhost:8000/v1/projects/
```

### Symptom: CORS Error in Browser

**Error in browser console:**
```
Access to XMLHttpRequest blocked by CORS policy
```

**Solution: Update CORS Settings**

Edit `.env.local`:
```env
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
# Or allow all (development only!)
CORS_ORIGINS=*
```

Restart:
```bash
docker-compose restart api
```

## Dashboard Issues

### Symptom: Dashboard Shows "Cannot connect to API"

**Check API is running:**
```bash
curl http://localhost:8000/health
```

**Check VITE_API_URL:**

In `.env.local`:
```env
VITE_API_URL=http://localhost:8000
```

**Rebuild dashboard:**
```bash
docker-compose build dashboard
docker-compose up -d dashboard
```

**Check browser console:**
Open http://localhost:3000, press F12, check console for errors.

### Symptom: Dashboard Page Blank

**Check logs:**
```bash
docker-compose logs dashboard | tail -50
```

**Clear browser cache:**
- Chrome: Ctrl+Shift+Delete
- Firefox: Ctrl+Shift+Delete
- Safari: Cmd+Option+E

**Hard refresh:**
- Chrome/Firefox: Ctrl+Shift+R
- Safari: Cmd+Shift+R

**Check for JavaScript errors:**
Open browser console (F12)

### Symptom: Dashboard Build Fails

**Error: "ENOSPC: no space left on device"**

```bash
# Clear npm cache
npm cache clean --force

# Increase inotify watchers (Linux)
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

**Error: "Module not found"**

```bash
cd dashboard
rm -rf node_modules package-lock.json
npm install
```

## Performance Issues

### Symptom: Slow API Responses

**Check system resources:**
```bash
docker stats
```

**Common causes:**

#### 1. Database Not Indexed

Add indexes to frequently queried columns (see [Database Issues](#symptom-slow-queries))

#### 2. Too Many Workers

```env
# .env.local
API_WORKERS=1  # Reduce to 1 for local development
```

#### 3. Debug Mode Enabled

```env
DEBUG=false
LOG_LEVEL=info
```

#### 4. Large Result Sets

Use pagination:
```bash
curl http://localhost:8000/v1/projects/{id}/database/vectors/list?limit=100&offset=0
```

### Symptom: High Memory Usage

**Check per-service usage:**
```bash
docker stats --no-stream
```

**Solutions:**

#### Reduce Database Pool Size
```env
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=5
```

#### Enable Qdrant Quantization
See [Vector Search Issues](#symptom-qdrant-out-of-memory)

#### Limit API Workers
```env
API_WORKERS=1
```

### Symptom: High Disk Usage

**Check usage:**
```bash
du -sh data/*
```

**Solutions:**

#### Clean Old Backups
```bash
rm -rf backups/*
```

#### Vacuum PostgreSQL
```bash
docker-compose exec postgres psql -U zerodb -d zerodb_local -c "VACUUM FULL;"
```

#### Prune Docker
```bash
docker system prune -a --volumes
```

#### Archive Old Data
See [Data Management Guide](./DATA_MANAGEMENT.md#data-archival)

## Cloud Sync Issues

### Symptom: "Authentication failed"

**Solution: Refresh API Key**

```bash
# Get new API key from https://www.ainative.studio/dashboard/api-keys

# Update .env.local
CLOUD_API_KEY=your-new-api-key

# Restart API
docker-compose restart api

# Re-login via CLI
zerodb cloud login
```

### Symptom: Sync Taking Too Long

**Check sync status:**
```bash
zerodb sync status
```

**Common causes:**

#### 1. Large Dataset

Use incremental sync:
```bash
zerodb sync apply --incremental
```

#### 2. Network Issues

Test connectivity:
```bash
curl https://api.ainative.studio/health
```

#### 3. Rate Limiting

Check logs for rate limit errors:
```bash
docker-compose logs api | grep -i "rate limit"
```

### Symptom: Sync Conflicts

**View conflicts:**
```bash
zerodb sync plan
```

**Resolve conflicts:**

Set conflict resolution strategy in `.env.local`:
```env
CONFLICT_RESOLUTION=newest-wins  # Options: local-wins, cloud-wins, newest-wins, manual
```

Or resolve manually:
```bash
zerodb sync resolve --interactive
```

## Docker Issues

### Symptom: "Cannot connect to Docker daemon"

**Check Docker is running:**
```bash
docker ps
```

**Start Docker:**
- macOS: Open Docker Desktop
- Linux: `sudo systemctl start docker`
- Windows: Start Docker Desktop

### Symptom: "No space left on device"

**Clean Docker:**
```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove everything unused
docker system prune -a --volumes
```

**Check disk space:**
```bash
df -h
```

### Symptom: Docker Build Fails

**Clear build cache:**
```bash
docker-compose build --no-cache
```

**Check Dockerfile:**
```bash
docker-compose config --quiet
```

## Network Issues

### Symptom: Services Can't Communicate

**Check Docker network:**
```bash
docker network ls
docker network inspect zerodb-local_default
```

**Recreate network:**
```bash
docker-compose down
docker-compose up -d
```

### Symptom: "DNS resolution failed"

**Test DNS:**
```bash
docker-compose exec api ping postgres
docker-compose exec api ping qdrant
```

**Solution: Use IP Addresses**

Find container IP:
```bash
docker inspect zerodb-postgres | grep IPAddress
```

Update connection string to use IP instead of hostname.

## Data Corruption

### Symptom: Database Won't Start After Crash

**Check logs:**
```bash
docker-compose logs postgres | grep -i error
```

**Solution 1: Repair Database**

```bash
docker-compose exec postgres pg_resetwal -f /var/lib/postgresql/data
docker-compose restart postgres
```

**Solution 2: Restore from Backup**

```bash
# Stop services
docker-compose down -v

# Restore backup (see Data Management guide)
./scripts/restore-local.sh backups/latest.tar.gz

# Start services
docker-compose up -d
```

### Symptom: Qdrant Collection Corrupted

**Delete and recreate collection:**

```bash
# Delete collection
curl -X DELETE http://localhost:6333/collections/{collection_name}

# Recreate collection
curl -X PUT http://localhost:6333/collections/{collection_name} \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 384,
      "distance": "Cosine"
    }
  }'
```

## Getting Additional Help

If none of these solutions work:

### 1. Gather Diagnostic Information

```bash
# Collect all logs
docker-compose logs > debug-logs.txt

# System information
docker version > system-info.txt
docker-compose version >> system-info.txt
uname -a >> system-info.txt

# Configuration
docker-compose config >> debug-config.txt
```

### 2. Report Issue

Open GitHub issue with:
- Description of problem
- Steps to reproduce
- Logs (debug-logs.txt)
- System info (system-info.txt)
- Configuration (debug-config.txt, redact secrets!)

https://github.com/AINative-Studio/core/issues

### 3. Community Support

- Discord: https://www.ainative.studio/community
- Email: hello@ainative.studio

## Quick Reference

### Restart Everything
```bash
docker-compose restart
```

### Reset Everything
```bash
docker-compose down -v && rm -rf data/ && docker-compose up -d
```

### View All Logs
```bash
docker-compose logs -f
```

### Check Service Health
```bash
docker-compose ps
curl http://localhost:8000/health
curl http://localhost:6333/healthz
```

### Check Resource Usage
```bash
docker stats
du -sh data/
df -h
```

## Summary

Most issues can be resolved by:
1. Checking logs
2. Restarting services
3. Verifying configuration
4. Checking system resources

For persistent issues, full reset is nuclear option:
```bash
docker-compose down -v
rm -rf data/
docker-compose up -d
```

Always keep backups before making major changes!

For more information:
- [Quick Start](./QUICK_START.md) - Initial setup
- [Environment Setup](./ENVIRONMENT_SETUP.md) - Configuration
- [Data Management](./DATA_MANAGEMENT.md) - Backups and recovery
