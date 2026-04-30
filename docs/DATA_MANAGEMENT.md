# ZeroDB Local - Data Management

Comprehensive guide to managing data in ZeroDB Local: backups, restores, migrations, scaling, and data lifecycle.

## Table of Contents

- [Data Storage Overview](#data-storage-overview)
- [Backup Strategies](#backup-strategies)
- [Restore Procedures](#restore-procedures)
- [Data Migration](#data-migration)
- [Data Lifecycle Management](#data-lifecycle-management)
- [Scaling Data Storage](#scaling-data-storage)
- [Data Cleanup and Maintenance](#data-cleanup-and-maintenance)
- [Performance Optimization](#performance-optimization)
- [Monitoring Data Usage](#monitoring-data-usage)
- [Disaster Recovery](#disaster-recovery)

## Data Storage Overview

ZeroDB Local persists data across multiple services, each with different storage characteristics:

### Storage Locations

| Service | Data Type | Storage Path | Volume Name | Approximate Size |
|---------|-----------|--------------|-------------|------------------|
| PostgreSQL | Relational data, metadata | `./data/postgres` | `postgres-data` | 100MB-10GB |
| Qdrant | Vector embeddings | `./data/qdrant` | `qdrant-data` | 500MB-50GB |
| MinIO | Object storage (files) | `./data/minio` | `minio-data` | Varies greatly |
| RedPanda | Event logs | `./data/redpanda` | `redpanda-data` | 100MB-5GB |
| Embeddings | Model cache | `./data/embeddings/models` | `embeddings-models` | 1GB-5GB |

### Data Directory Structure

```
zerodb-local/
├── data/
│   ├── postgres/           # PostgreSQL data files
│   │   ├── base/          # Database files
│   │   ├── pg_wal/        # Write-ahead logs
│   │   └── pg_stat/       # Statistics
│   ├── qdrant/            # Qdrant collections
│   │   ├── collections/   # Vector data
│   │   ├── snapshots/     # Collection snapshots
│   │   └── wal/           # Write-ahead logs
│   ├── minio/             # MinIO buckets
│   │   └── zerodb-local/  # Default bucket
│   ├── redpanda/          # RedPanda topics
│   │   └── kafka/         # Event data
│   └── embeddings/
│       └── models/        # Downloaded models
└── backups/               # Backup storage (created by scripts)
```

### Data Persistence

All data is stored in Docker volumes mapped to local directories:

```yaml
# docker-compose.yml
volumes:
  postgres-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ./data/postgres

  # Similar for other services...
```

**Key characteristics:**
- Data survives container restarts
- Data is lost if volumes are deleted (`docker-compose down -v`)
- Data can be backed up by copying directories
- Data is accessible from host filesystem

## Backup Strategies

### Automated Backup Script

ZeroDB Local includes a backup script for one-command backups:

```bash
# Run backup script
./scripts/backup-local.sh

# Output: ./backups/zerodb-backup-2026-02-27-155230.tar.gz
```

**What gets backed up:**
- All PostgreSQL databases
- All Qdrant collections
- All MinIO buckets
- All RedPanda topics
- Configuration files (`.env.local`, `docker-compose.yml`)

### Manual Backup

#### 1. Stop All Services (Recommended)

For consistent backups, stop all services first:

```bash
docker-compose down
```

#### 2. Backup Data Directories

```bash
# Create backup directory
mkdir -p backups

# Create timestamped backup
BACKUP_NAME="zerodb-backup-$(date +%Y-%m-%d-%H%M%S)"
tar -czf "backups/${BACKUP_NAME}.tar.gz" \
  data/ \
  .env.local \
  docker-compose.yml

echo "Backup created: backups/${BACKUP_NAME}.tar.gz"
```

#### 3. Restart Services

```bash
docker-compose up -d
```

### Service-Specific Backups

#### PostgreSQL Backup (Hot Backup)

Backup while services are running:

```bash
# Dump all databases
docker-compose exec postgres pg_dumpall -U zerodb > backups/postgres-$(date +%Y%m%d).sql

# Dump specific database
docker-compose exec postgres pg_dump -U zerodb zerodb_local > backups/zerodb_local-$(date +%Y%m%d).sql

# Dump with compression
docker-compose exec postgres pg_dump -U zerodb zerodb_local | gzip > backups/zerodb_local-$(date +%Y%m%d).sql.gz
```

#### Qdrant Backup (Snapshot)

```bash
# Create snapshot via API
curl -X POST http://localhost:6333/collections/{collection_name}/snapshots

# List snapshots
curl http://localhost:6333/collections/{collection_name}/snapshots

# Download snapshot
curl http://localhost:6333/collections/{collection_name}/snapshots/{snapshot_name} \
  --output backups/qdrant-{collection_name}-$(date +%Y%m%d).snapshot
```

#### MinIO Backup

```bash
# Install MinIO client
brew install minio/stable/mc  # macOS
# or
wget https://dl.min.io/client/mc/release/linux-amd64/mc  # Linux

# Configure MinIO client
mc alias set local http://localhost:9000 minioadmin minioadmin

# Mirror bucket to local directory
mc mirror local/zerodb-local backups/minio-$(date +%Y%m%d)

# Create tarball
tar -czf backups/minio-$(date +%Y%m%d).tar.gz backups/minio-$(date +%Y%m%d)
```

#### RedPanda Backup

```bash
# Backup topic data
docker-compose exec redpanda rpk topic consume {topic_name} \
  --offset start \
  --num-messages 0 \
  > backups/redpanda-{topic_name}-$(date +%Y%m%d).jsonl
```

### Scheduled Backups

#### Using Cron (Linux/macOS)

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/zerodb-local && ./scripts/backup-local.sh >> logs/backup.log 2>&1

# Add weekly backup on Sundays at 3 AM
0 3 * * 0 cd /path/to/zerodb-local && ./scripts/backup-local.sh >> logs/backup.log 2>&1
```

#### Using systemd Timer (Linux)

```bash
# Create service file: /etc/systemd/system/zerodb-backup.service
[Unit]
Description=ZeroDB Local Backup

[Service]
Type=oneshot
User=your-username
WorkingDirectory=/path/to/zerodb-local
ExecStart=/path/to/zerodb-local/scripts/backup-local.sh

# Create timer file: /etc/systemd/system/zerodb-backup.timer
[Unit]
Description=ZeroDB Local Backup Timer

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target

# Enable and start timer
sudo systemctl enable zerodb-backup.timer
sudo systemctl start zerodb-backup.timer
sudo systemctl status zerodb-backup.timer
```

### Backup to Cloud Storage

#### AWS S3

```bash
# Install AWS CLI
pip install awscli

# Configure AWS credentials
aws configure

# Upload backup to S3
BACKUP_FILE="backups/zerodb-backup-$(date +%Y-%m-%d).tar.gz"
./scripts/backup-local.sh
aws s3 cp "$BACKUP_FILE" s3://your-bucket/zerodb-backups/
```

#### Google Cloud Storage

```bash
# Install gcloud CLI
# https://cloud.google.com/sdk/docs/install

# Upload backup
BACKUP_FILE="backups/zerodb-backup-$(date +%Y-%m-%d).tar.gz"
./scripts/backup-local.sh
gsutil cp "$BACKUP_FILE" gs://your-bucket/zerodb-backups/
```

### Backup Retention Policy

Implement a retention policy to manage backup storage:

```bash
# Keep last 7 daily backups
find backups/ -name "zerodb-backup-*.tar.gz" -mtime +7 -delete

# Keep last 4 weekly backups
# (Run this script weekly, keeping backups older than 28 days)
find backups/ -name "zerodb-backup-weekly-*.tar.gz" -mtime +28 -delete

# Keep last 12 monthly backups
find backups/ -name "zerodb-backup-monthly-*.tar.gz" -mtime +365 -delete
```

Add to backup script:

```bash
# scripts/backup-local.sh
# ... backup logic ...

# Cleanup old backups
find backups/ -name "zerodb-backup-*.tar.gz" -mtime +7 -delete
```

## Restore Procedures

### Full System Restore

Restore from a complete backup:

```bash
# 1. Stop all services
docker-compose down -v  # -v removes volumes

# 2. Extract backup
tar -xzf backups/zerodb-backup-2026-02-27-155230.tar.gz

# 3. Start services
docker-compose up -d

# 4. Verify restore
docker-compose ps
curl http://localhost:8000/health
```

### Restore Using Script

```bash
./scripts/restore-local.sh backups/zerodb-backup-2026-02-27-155230.tar.gz
```

### Service-Specific Restores

#### PostgreSQL Restore

```bash
# Stop API server to prevent connections
docker-compose stop api

# Restore from SQL dump
docker-compose exec -T postgres psql -U zerodb zerodb_local < backups/zerodb_local-20260227.sql

# Or restore compressed dump
gunzip -c backups/zerodb_local-20260227.sql.gz | docker-compose exec -T postgres psql -U zerodb zerodb_local

# Restart API
docker-compose start api
```

#### Qdrant Restore

```bash
# Upload snapshot via API
curl -X PUT http://localhost:6333/collections/{collection_name}/snapshots/upload \
  -H "Content-Type: application/octet-stream" \
  --data-binary @backups/qdrant-{collection_name}-20260227.snapshot

# Restore from snapshot
curl -X PUT http://localhost:6333/collections/{collection_name}/snapshots/{snapshot_name}/recover
```

#### MinIO Restore

```bash
# Stop MinIO
docker-compose stop minio

# Clear existing data
rm -rf data/minio/zerodb-local/*

# Extract backup
tar -xzf backups/minio-20260227.tar.gz -C data/minio/

# Start MinIO
docker-compose start minio
```

### Point-in-Time Recovery

For PostgreSQL point-in-time recovery:

```bash
# Enable WAL archiving in docker-compose.yml
services:
  postgres:
    command:
      - "postgres"
      - "-c"
      - "wal_level=replica"
      - "-c"
      - "archive_mode=on"
      - "-c"
      - "archive_command=cp %p /var/lib/postgresql/data/pg_wal_archive/%f"
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
      - ./data/postgres-wal-archive:/var/lib/postgresql/data/pg_wal_archive

# Restore to specific point in time
# 1. Restore base backup
# 2. Create recovery.conf
# 3. Replay WAL logs to target time
```

## Data Migration

### Migrate Between Environments

#### Export from Local

```bash
# Export all data
./scripts/backup-local.sh

# Or export specific project
curl http://localhost:8000/v1/projects/{project_id}/export > project-export.json
```

#### Import to Another Environment

```bash
# Copy backup to target machine
scp backups/zerodb-backup-2026-02-27.tar.gz user@target-host:/path/to/zerodb-local/backups/

# On target machine
./scripts/restore-local.sh backups/zerodb-backup-2026-02-27.tar.gz

# Or import specific project
curl -X POST http://target-host:8000/v1/projects/import \
  -H "Content-Type: application/json" \
  -d @project-export.json
```

### Migrate to ZeroDB Cloud

```bash
# 1. Install CLI
cd cli
pip install -e .

# 2. Login to cloud
zerodb cloud login

# 3. Link local project to cloud
zerodb cloud link {cloud_project_id}

# 4. Sync to cloud
zerodb sync apply

# 5. Verify sync
zerodb sync status
```

### Migrate from ZeroDB Cloud to Local

```bash
# 1. Login to cloud
zerodb cloud login

# 2. Create local project
curl -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "cloud-project-local"}'

# 3. Link and pull
zerodb cloud link {cloud_project_id}
zerodb cloud pull

# 4. Verify data
curl http://localhost:8000/v1/projects/{local_project_id}/database/vectors/list
```

## Data Lifecycle Management

### Data Retention Policies

#### Automatic Cleanup for Old Vectors

```python
# scripts/cleanup_old_vectors.py
import requests
from datetime import datetime, timedelta

API_URL = "http://localhost:8000"
PROJECT_ID = "your-project-id"

# Delete vectors older than 90 days
cutoff_date = datetime.now() - timedelta(days=90)

# Query old vectors
response = requests.post(
    f"{API_URL}/v1/projects/{PROJECT_ID}/database/vectors/query",
    json={
        "filter": {
            "created_at": {"$lt": cutoff_date.isoformat()}
        }
    }
)

old_vectors = response.json()["results"]

# Delete old vectors
for vector in old_vectors:
    requests.delete(
        f"{API_URL}/v1/projects/{PROJECT_ID}/database/vectors/{vector['id']}"
    )

print(f"Deleted {len(old_vectors)} old vectors")
```

#### Event Log Rotation

```bash
# Prune RedPanda topics older than 7 days
docker-compose exec redpanda rpk topic alter-config {topic_name} \
  --set retention.ms=604800000  # 7 days in milliseconds
```

### Data Archival

Archive old data to cold storage:

```bash
# 1. Export old data
curl http://localhost:8000/v1/projects/{project_id}/database/vectors/export \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {"created_at": {"$lt": "2026-01-01T00:00:00Z"}},
    "format": "parquet"
  }' \
  --output archives/vectors-2025.parquet

# 2. Delete archived data
curl -X DELETE http://localhost:8000/v1/projects/{project_id}/database/vectors/bulk \
  -H "Content-Type: application/json" \
  -d '{"filter": {"created_at": {"$lt": "2026-01-01T00:00:00Z"}}}'

# 3. Upload archive to S3
aws s3 cp archives/vectors-2025.parquet s3://your-archive-bucket/
```

## Scaling Data Storage

### Increase Storage Capacity

#### Add More Disk Space

```bash
# Check current disk usage
df -h data/

# If running out of space, move data to larger disk
# 1. Stop services
docker-compose down

# 2. Copy data to new location
sudo rsync -av data/ /mnt/larger-disk/zerodb-data/

# 3. Update docker-compose.yml
# Change volume paths to /mnt/larger-disk/zerodb-data/

# 4. Start services
docker-compose up -d
```

#### Use External Storage

Mount network storage or cloud block storage:

```yaml
# docker-compose.yml
services:
  postgres:
    volumes:
      - /mnt/nfs/zerodb/postgres:/var/lib/postgresql/data

  minio:
    volumes:
      - /mnt/s3fs/zerodb/minio:/data
```

### Horizontal Scaling

For large datasets, consider:

#### Sharding by Project

Run multiple ZeroDB Local instances, one per major project:

```bash
# Instance 1 (projects A-M)
cd zerodb-local-1
docker-compose -p zerodb1 up -d

# Instance 2 (projects N-Z)
cd zerodb-local-2
docker-compose -p zerodb2 up -d
```

#### Read Replicas (PostgreSQL)

```yaml
# docker-compose.yml
services:
  postgres-primary:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_USER: zerodb
      POSTGRES_PASSWORD: localpass
    volumes:
      - ./data/postgres-primary:/var/lib/postgresql/data

  postgres-replica:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_MASTER_SERVICE_HOST: postgres-primary
      POSTGRES_MASTER_SERVICE_PORT: 5432
    volumes:
      - ./data/postgres-replica:/var/lib/postgresql/data
```

## Data Cleanup and Maintenance

### Vacuum PostgreSQL

Regular maintenance for optimal performance:

```bash
# Analyze all tables
docker-compose exec postgres psql -U zerodb -d zerodb_local -c "ANALYZE;"

# Vacuum all tables
docker-compose exec postgres psql -U zerodb -d zerodb_local -c "VACUUM ANALYZE;"

# Full vacuum (requires more time and space)
docker-compose exec postgres psql -U zerodb -d zerodb_local -c "VACUUM FULL;"
```

### Optimize Qdrant Collections

```bash
# Optimize collection
curl -X POST http://localhost:6333/collections/{collection_name}/optimize

# Compact collection (remove deleted vectors)
curl -X POST http://localhost:6333/collections/{collection_name}/optimize \
  -H "Content-Type: application/json" \
  -d '{"optimizers_config": {"indexing_threshold": 10000}}'
```

### Clean MinIO Unused Files

```bash
# List buckets
mc ls local/

# Remove incomplete uploads
mc rm --recursive --force --incomplete local/zerodb-local/

# Remove old versions (if versioning enabled)
mc rm --recursive --force --versions local/zerodb-local/
```

### Prune Docker Volumes

```bash
# Remove unused volumes (be careful!)
docker volume prune

# Remove specific volume
docker volume rm zerodb-local_postgres-data
```

## Performance Optimization

### Database Indexing

Add indexes for frequently queried columns:

```sql
-- Connect to PostgreSQL
docker-compose exec postgres psql -U zerodb -d zerodb_local

-- Create indexes
CREATE INDEX idx_vectors_created_at ON vectors(created_at);
CREATE INDEX idx_vectors_metadata ON vectors USING GIN(metadata);
CREATE INDEX idx_events_timestamp ON events(timestamp);
```

### Qdrant Performance Tuning

```bash
# Increase HNSW parameters for better search quality (slower indexing)
curl -X PATCH http://localhost:6333/collections/{collection_name} \
  -H "Content-Type: application/json" \
  -d '{
    "hnsw_config": {
      "m": 32,
      "ef_construct": 200
    }
  }'

# Enable quantization for memory efficiency
curl -X PUT http://localhost:6333/collections/{collection_name}/quantization \
  -H "Content-Type: application/json" \
  -d '{
    "scalar": {
      "type": "int8",
      "quantile": 0.99
    }
  }'
```

### MinIO Performance

```bash
# Enable caching
# Add to docker-compose.yml
services:
  minio:
    environment:
      MINIO_CACHE: "on"
      MINIO_CACHE_DRIVES: "/tmp/cache"
      MINIO_CACHE_QUOTA: 80  # Use 80% of cache drive
```

## Monitoring Data Usage

### Check Disk Usage

```bash
# Overall disk usage
du -sh data/

# Per-service usage
du -sh data/*

# Detailed breakdown
du -h data/ | sort -hr | head -20
```

### Database Size

```bash
# PostgreSQL database size
docker-compose exec postgres psql -U zerodb -d zerodb_local -c "\l+"

# Table sizes
docker-compose exec postgres psql -U zerodb -d zerodb_local -c "
  SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
  FROM pg_tables
  WHERE schemaname = 'public'
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

### Qdrant Statistics

```bash
# Collection stats
curl http://localhost:6333/collections/{collection_name}

# All collections
curl http://localhost:6333/collections
```

### MinIO Statistics

```bash
# Bucket usage
mc du local/zerodb-local

# Detailed usage
mc du --recursive local/zerodb-local
```

## Disaster Recovery

### Disaster Recovery Plan

1. **Regular Backups**: Automated daily backups to multiple locations
2. **Offsite Storage**: Keep backups in different geographic locations
3. **Backup Testing**: Regularly test restore procedures
4. **Documentation**: Keep recovery runbooks updated
5. **Monitoring**: Alert on backup failures

### Recovery Time Objective (RTO) and Recovery Point Objective (RPO)

| Scenario | RPO | RTO | Strategy |
|----------|-----|-----|----------|
| Accidental deletion | 1 hour | 15 minutes | Hourly snapshots |
| Service failure | 24 hours | 30 minutes | Daily backups |
| Disk failure | 24 hours | 2 hours | Daily backups + redundancy |
| Total system loss | 7 days | 4 hours | Weekly offsite backups |

### Emergency Recovery Checklist

- [ ] Identify failure scope (service, disk, system)
- [ ] Stop affected services
- [ ] Locate most recent valid backup
- [ ] Verify backup integrity
- [ ] Restore data from backup
- [ ] Restart services
- [ ] Verify data integrity
- [ ] Check application functionality
- [ ] Monitor for issues
- [ ] Document incident
- [ ] Update disaster recovery plan

### Multi-Region Backup Strategy

For critical data:

```bash
# Backup to multiple regions
BACKUP_FILE="backups/zerodb-backup-$(date +%Y-%m-%d).tar.gz"
./scripts/backup-local.sh

# Upload to multiple cloud regions
aws s3 cp "$BACKUP_FILE" s3://backup-us-west-2/zerodb/
aws s3 cp "$BACKUP_FILE" s3://backup-eu-central-1/zerodb/
aws s3 cp "$BACKUP_FILE" s3://backup-ap-southeast-1/zerodb/
```

## Summary

Effective data management in ZeroDB Local requires:

- **Regular Backups**: Automated daily backups with retention policies
- **Tested Restores**: Regularly verify backup integrity
- **Performance Optimization**: Index databases, tune configurations
- **Monitoring**: Track disk usage and set up alerts
- **Lifecycle Policies**: Archive old data, clean up unused resources
- **Disaster Recovery**: Maintain offsite backups and recovery procedures

Key commands:
```bash
# Backup
./scripts/backup-local.sh

# Restore
./scripts/restore-local.sh backups/zerodb-backup-2026-02-27.tar.gz

# Check usage
du -sh data/

# Optimize
docker-compose exec postgres psql -U zerodb -d zerodb_local -c "VACUUM ANALYZE;"
```

For more information:
- [Quick Start](./QUICK_START.md) - Initial setup
- [Environment Setup](./ENVIRONMENT_SETUP.md) - Configuration
- [Troubleshooting](./TROUBLESHOOTING.md) - Common issues
- [Sync Strategy](./SYNC_STRATEGY.md) - Cloud synchronization
