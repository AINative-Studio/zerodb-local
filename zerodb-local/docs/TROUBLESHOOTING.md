# Troubleshooting Guide

This guide covers common issues when running ZeroDB Local and their solutions.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Docker Issues](#docker-issues)
- [Service-Specific Issues](#service-specific-issues)
- [Network & Connectivity](#network--connectivity)
- [Performance Issues](#performance-issues)
- [Data Issues](#data-issues)
- [Sync Issues](#sync-issues)
- [Advanced Debugging](#advanced-debugging)

---

## Quick Diagnostics

### Run Full Health Check

```bash
# Overall health
curl http://localhost:8000/health | jq

# Check all services
docker-compose ps

# View recent logs
docker-compose logs --tail=100

# Check disk space
df -h .
du -sh data/
```

### Common Quick Fixes

```bash
# 1. Restart all services
docker-compose restart

# 2. Full restart (clears caches)
docker-compose down && docker-compose up -d

# 3. Check for updates
docker-compose pull

# 4. Fix file permissions
sudo chown -R $(id -u):$(id -g) data/
```

---

## Docker Issues

### Docker Daemon Not Running

**Symptoms:**
```
Cannot connect to the Docker daemon
```

**Solution:**
```bash
# macOS/Windows: Start Docker Desktop
open -a Docker  # macOS

# Linux: Start Docker service
sudo systemctl start docker
sudo systemctl enable docker  # Auto-start on boot

# Verify Docker is running
docker info
```

### Docker Compose Not Found

**Symptoms:**
```
docker-compose: command not found
```

**Solution:**
```bash
# Option 1: Use docker compose (v2 syntax)
docker compose up -d

# Option 2: Install docker-compose standalone
# macOS (Homebrew)
brew install docker-compose

# Linux
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Out of Disk Space

**Symptoms:**
```
no space left on device
```

**Solution:**
```bash
# Check Docker disk usage
docker system df

# Clean up unused containers
docker system prune -a

# Clean up volumes (⚠️ WARNING: This deletes data!)
docker volume prune

# Check ZeroDB data size
du -sh data/
find backups/ -name "*.tar.gz" -mtime +7 -delete  # Remove old backups
```

### Out of Memory

**Symptoms:**
```
Container keeps restarting
OOMKilled in docker-compose logs
```

**Solution:**
```bash
# Check Docker resource limits
docker stats

# Increase Docker Desktop memory limit
# Docker Desktop > Settings > Resources > Memory
# Set to at least 8GB

# Reduce memory usage (in .env.local)
DB_POOL_SIZE=20           # Reduce from 50
API_WORKERS=2             # Reduce from 4
EMBEDDINGS_MODEL=BAAI/bge-small-en-v1.5  # Use smaller model
```

### Port Already in Use

**Symptoms:**
```
Bind for 0.0.0.0:8000 failed: port is already allocated
```

**Solution:**
```bash
# Find what's using the port
lsof -i :8000  # Replace 8000 with your conflicting port

# Kill the process
kill -9 <PID>

# Or change ports in docker-compose.yml
# Edit ports section:
ports:
  - "8001:8000"  # Map host 8001 to container 8000
```

---

## Service-Specific Issues

### PostgreSQL Issues

#### Database Won't Start

**Symptoms:**
```bash
docker-compose logs postgres
# ERROR: database files are incompatible with server
```

**Solution:**
```bash
# Stop services
docker-compose down

# Backup current data (if possible)
cp -r data/postgres data/postgres.backup

# Remove corrupted data
rm -rf data/postgres

# Restart (will reinitialize)
docker-compose up -d postgres

# Restore from backup if needed
./scripts/restore-local.sh
```

#### Connection Refused

**Symptoms:**
```
could not connect to server: Connection refused
```

**Solution:**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres | tail -50

# Verify PostgreSQL is ready
docker-compose exec postgres pg_isready -U zerodb

# Connect manually to test
docker-compose exec postgres psql -U zerodb -d zerodb_local
```

#### Slow Queries

**Symptoms:**
- API responses take >5 seconds
- High CPU usage on postgres container

**Solution:**
```bash
# Connect to database
docker-compose exec postgres psql -U zerodb -d zerodb_local

# Check slow queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;

# Run VACUUM to reclaim space
VACUUM ANALYZE;

# Check missing indexes
SELECT schemaname, tablename, attname, n_distinct
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY n_distinct DESC;
```

### Qdrant Issues

#### Qdrant Won't Start

**Symptoms:**
```
Error: cannot create collection
```

**Solution:**
```bash
# Check Qdrant logs
docker-compose logs qdrant

# Verify Qdrant is accessible
curl http://localhost:6333/healthz

# Clear Qdrant data and restart
docker-compose down
rm -rf data/qdrant
docker-compose up -d qdrant

# Reinitialize collections
curl -X POST http://localhost:8000/v1/admin/qdrant/initialize
```

#### Search Returns No Results

**Symptoms:**
- Search queries return empty results
- Vectors were successfully inserted

**Solution:**
```bash
# Check if collection exists
curl http://localhost:6333/collections | jq

# Check collection stats
curl http://localhost:6333/collections/zerodb_local | jq

# Verify vector count
curl http://localhost:6333/collections/zerodb_local/points/count | jq

# Re-index collection
curl -X POST http://localhost:6333/collections/zerodb_local/indexes/rebuild
```

#### High Memory Usage

**Symptoms:**
```bash
docker stats
# qdrant using >4GB memory
```

**Solution:**
```bash
# Optimize Qdrant collection
curl -X POST http://localhost:6333/collections/zerodb_local/optimize

# Reduce index size (in API configuration)
QDRANT_M=8              # Reduce from 16
QDRANT_EF_CONSTRUCT=50  # Reduce from 100

# Restart Qdrant
docker-compose restart qdrant
```

### MinIO Issues

#### MinIO Console Not Accessible

**Symptoms:**
- Cannot access http://localhost:9001

**Solution:**
```bash
# Check MinIO is running
docker-compose ps minio

# Check MinIO logs
docker-compose logs minio

# Verify MinIO health
curl http://localhost:9000/minio/health/live

# Restart MinIO
docker-compose restart minio
```

#### File Upload Fails

**Symptoms:**
```
Access Denied
```

**Solution:**
```bash
# Check MinIO credentials in .env.local
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Verify bucket exists
docker-compose exec minio mc ls local/

# Create bucket manually if needed
docker-compose exec minio mc mb local/zerodb-local-files

# Set bucket policy to public (development only!)
docker-compose exec minio mc anonymous set public local/zerodb-local-files
```

#### Bucket Not Found

**Symptoms:**
```
NoSuchBucket: The specified bucket does not exist
```

**Solution:**
```bash
# List existing buckets
docker-compose exec minio mc ls local/

# Create missing bucket
BUCKET_NAME="zerodb-local-files"
docker-compose exec minio mc mb local/${BUCKET_NAME}

# Verify bucket creation
docker-compose exec minio mc ls local/${BUCKET_NAME}
```

### RedPanda Issues

#### RedPanda Won't Start

**Symptoms:**
```
Error: failed to initialize data directory
```

**Solution:**
```bash
# Check RedPanda logs
docker-compose logs redpanda

# Clear RedPanda data and restart
docker-compose down
rm -rf data/redpanda
docker-compose up -d redpanda

# Verify RedPanda is running
docker-compose exec redpanda rpk cluster info
```

#### Events Not Appearing

**Symptoms:**
- Events created but not showing in listings

**Solution:**
```bash
# Check if topic exists
docker-compose exec redpanda rpk topic list

# Create topic manually
docker-compose exec redpanda rpk topic create zerodb-local-events

# Check consumer groups
docker-compose exec redpanda rpk group list

# View topic messages
docker-compose exec redpanda rpk topic consume zerodb-local-events --num 10
```

### Embeddings Service Issues

#### Model Download Stuck

**Symptoms:**
- Embeddings service logs show "Downloading model..."
- Service doesn't become healthy

**Solution:**
```bash
# Check embeddings service logs
docker-compose logs embeddings -f

# Model download can take 2-5 minutes on first run
# Wait for: "✅ Model loaded successfully"

# If stuck, restart with clean cache
docker-compose down
rm -rf data/embeddings/models
docker-compose up -d embeddings

# Monitor download progress
watch -n 2 'docker-compose logs embeddings --tail=10'
```

#### Embeddings Generation Slow

**Symptoms:**
- Embedding requests take >5 seconds

**Solution:**
```bash
# Check if GPU is available (if you have NVIDIA GPU)
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# Use GPU in .env.local
EMBEDDINGS_DEVICE=cuda

# Or use smaller model
EMBEDDINGS_MODEL=BAAI/bge-small-en-v1.5  # 384 dims, fastest

# Restart embeddings service
docker-compose restart embeddings
```

#### Model Not Loading

**Symptoms:**
```
Error loading model: Could not find model
```

**Solution:**
```bash
# Check model name is correct
# Valid models:
# - BAAI/bge-small-en-v1.5 (384 dims)
# - BAAI/bge-base-en-v1.5 (768 dims)
# - BAAI/bge-large-en-v1.5 (1024 dims)

# Update .env.local
EMBEDDINGS_MODEL=BAAI/bge-small-en-v1.5

# Clear cache and restart
rm -rf data/embeddings/models
docker-compose restart embeddings
```

---

## Network & Connectivity

### Can't Access API

**Symptoms:**
```
curl: (7) Failed to connect to localhost port 8000
```

**Solution:**
```bash
# Check if API is running
docker-compose ps zerodb-api

# Check API logs
docker-compose logs zerodb-api

# Verify port is exposed
docker-compose port zerodb-api 8000

# Check firewall isn't blocking
sudo ufw status  # Linux
# Or disable macOS firewall temporarily

# Test from within container
docker-compose exec zerodb-api curl http://localhost:8000/health
```

### CORS Errors in Browser

**Symptoms:**
```
Access to fetch at 'http://localhost:8000' has been blocked by CORS policy
```

**Solution:**
```bash
# Add your frontend origin to .env.local
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# For development, allow all origins (NOT for production!)
CORS_ORIGINS=*

# Restart API
docker-compose restart zerodb-api
```

### Services Can't Communicate

**Symptoms:**
```
Error: could not resolve host: postgres
```

**Solution:**
```bash
# Verify all services are on same network
docker network ls
docker network inspect zerodb_zerodb-network

# Check service connectivity
docker-compose exec zerodb-api ping postgres
docker-compose exec zerodb-api curl http://qdrant:6333/healthz

# Recreate network
docker-compose down
docker-compose up -d
```

---

## Performance Issues

### API Slow to Respond

**Symptoms:**
- API requests take >2 seconds
- High CPU usage

**Solution:**
```bash
# Check resource usage
docker stats

# Increase worker count in .env.local
API_WORKERS=8  # Increase from 4

# Increase database pool
DB_POOL_SIZE=100
DB_MAX_OVERFLOW=50

# Enable query caching
ENABLE_QUERY_CACHE=true

# Restart services
docker-compose restart zerodb-api
```

### Vector Search Slow

**Symptoms:**
- Search queries take >1 second
- Qdrant using high CPU

**Solution:**
```bash
# Optimize Qdrant index
curl -X POST http://localhost:6333/collections/zerodb_local/optimize

# Tune search parameters in .env.local
QDRANT_EF_CONSTRUCT=200  # Increase for better accuracy
QDRANT_M=16              # Increase for faster search

# Use faster distance metric
QDRANT_DISTANCE=dot      # Instead of cosine

# Create better indexes
curl -X PUT http://localhost:6333/collections/zerodb_local/index \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "metadata.category",
    "field_schema": "keyword"
  }'
```

### Database Connection Pool Exhausted

**Symptoms:**
```
QueuePool limit of size 20 overflow 10 reached
```

**Solution:**
```bash
# Increase pool size in .env.local
DB_POOL_SIZE=100         # Increase from 20
DB_MAX_OVERFLOW=50       # Increase from 10
DB_POOL_RECYCLE=3600     # Recycle connections after 1 hour

# Restart API
docker-compose restart zerodb-api

# Monitor active connections
docker-compose exec postgres psql -U zerodb -d zerodb_local -c "SELECT count(*) FROM pg_stat_activity;"
```

---

## Data Issues

### Data Lost After Restart

**Symptoms:**
- Data disappears after `docker-compose down`

**Solution:**
```bash
# Check if volumes are properly mounted
docker-compose config | grep -A 5 volumes

# Verify data directories exist
ls -la data/
# Should see: postgres/, qdrant/, minio/, redpanda/

# Don't use -v flag when stopping
docker-compose down      # ✅ Keeps data
docker-compose down -v   # ❌ DELETES ALL DATA!

# Create backup before operations
./scripts/backup-local.sh
```

### Vector Embeddings Inconsistent

**Symptoms:**
- Same text produces different embeddings

**Solution:**
```bash
# Ensure normalization is consistent
# In API requests, always use:
{
  "normalize": true  # or always false
}

# Check embeddings service consistency
curl -X POST http://localhost:8001/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["test"],
    "normalize": true
  }' | jq '.embeddings[0][0:5]'

# Regenerate embeddings if needed
curl -X POST http://localhost:8000/v1/projects/${PROJECT_ID}/database/vectors/reindex
```

### Duplicate Vectors

**Symptoms:**
- Search returns duplicate results

**Solution:**
```bash
# Check for duplicates in PostgreSQL
docker-compose exec postgres psql -U zerodb -d zerodb_local -c "
SELECT document, COUNT(*)
FROM vectors
GROUP BY document
HAVING COUNT(*) > 1;
"

# Remove duplicates (keeps newest)
curl -X POST http://localhost:8000/v1/admin/vectors/deduplicate \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "your-project-id",
    "keep": "newest"
  }'
```

---

## Sync Issues

### Can't Connect to Cloud

**Symptoms:**
```
Error: Unauthorized - Invalid API key
```

**Solution:**
```bash
# Verify API key is correct
# Get from: https://www.ainative.studio/dashboard/api-keys

# Update .env.local
CLOUD_API_KEY=your-api-key-here
CLOUD_API_URL=https://api.ainative.studio

# Restart API
docker-compose restart zerodb-api

# Test connection
curl -X GET https://api.ainative.studio/v1/auth/verify \
  -H "Authorization: Bearer ${CLOUD_API_KEY}"
```

### Sync Conflicts

**Symptoms:**
```
Error: Conflict detected - manual resolution required
```

**Solution:**
```bash
# View conflicting items
curl http://localhost:8000/v1/sync/conflicts | jq

# Resolve with strategy (in .env.local)
CONFLICT_RESOLUTION=newest-wins  # Or: local-wins, cloud-wins, manual

# Force sync with chosen strategy
curl -X POST http://localhost:8000/v1/sync/apply \
  -H "Content-Type: application/json" \
  -d '{
    "force": true,
    "strategy": "newest-wins"
  }'
```

---

## Advanced Debugging

### Enable Debug Logging

```bash
# In .env.local
DEBUG=true
LOG_LEVEL=debug
SQL_ECHO=true

# Restart services
docker-compose restart

# View detailed logs
docker-compose logs -f zerodb-api
```

### Inspect Database Schema

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U zerodb -d zerodb_local

# List all tables
\dt

# Describe table schema
\d vectors
\d projects
\d table_rows

# View indexes
\di

# Check table sizes
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Monitor Resource Usage

```bash
# Real-time resource monitoring
docker stats

# CPU and memory per service
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Network usage
docker stats --format "table {{.Name}}\t{{.NetIO}}"

# Disk I/O
docker stats --format "table {{.Name}}\t{{.BlockIO}}"
```

### Export Logs for Support

```bash
# Export all logs
docker-compose logs > zerodb-logs.txt

# Export specific service logs
docker-compose logs zerodb-api > api-logs.txt

# Export with timestamps
docker-compose logs --timestamps > zerodb-logs-timestamped.txt

# Last 1000 lines only
docker-compose logs --tail=1000 > zerodb-logs-recent.txt
```

### Health Check Scripts

```bash
#!/bin/bash
# health-check.sh - Comprehensive health check

echo "=== Docker Status ==="
docker info | head -5

echo "\n=== Service Status ==="
docker-compose ps

echo "\n=== API Health ==="
curl -s http://localhost:8000/health | jq '.status, .summary'

echo "\n=== Individual Services ==="
curl -s http://localhost:6333/healthz && echo "Qdrant: OK" || echo "Qdrant: FAIL"
curl -s http://localhost:9000/minio/health/live && echo "MinIO: OK" || echo "MinIO: FAIL"
curl -s http://localhost:8001/health | jq '.status' || echo "Embeddings: FAIL"

echo "\n=== Disk Usage ==="
df -h . | tail -1
du -sh data/

echo "\n=== Resource Usage ==="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

---

## Getting Help

If you're still experiencing issues:

1. **Check Documentation**:
   - [Quick Start Guide](./QUICK_START.md)
   - [Environment Setup](./ENVIRONMENT_SETUP.md)
   - [Data Management](./DATA_MANAGEMENT.md)

2. **Search GitHub Issues**:
   - https://github.com/ainative/core/issues

3. **Create New Issue**:
   - Include output of `docker-compose ps`
   - Include recent logs: `docker-compose logs --tail=100`
   - Describe what you were doing when the error occurred
   - Include your environment: OS, Docker version, RAM, CPU

4. **Contact Support**:
   - Email: hello@ainative.studio
   - Community: https://www.ainative.studio/community

---

**Pro Tip**: Most issues can be resolved by running the health check script above and inspecting the logs with `docker-compose logs`.
