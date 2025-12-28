# Data Management Guide

This guide explains how to manage persistent data in ZeroDB Local, including backups, restores, and data lifecycle management.

## Overview

ZeroDB Local stores data in persistent Docker volumes, ensuring data survives container restarts. All data is stored in the `./data/` directory:

```
data/
├── postgres/       # PostgreSQL database files
├── qdrant/         # Qdrant vector collections
├── minio/          # MinIO object storage
├── redpanda/       # RedPanda event logs
└── embeddings/     # BGE model cache
```

## Data Persistence

### Docker Volumes

All services use bind mounts to local directories for data persistence:

```yaml
# docker-compose.yml
services:
  postgres:
    volumes:
      - ./data/postgres:/var/lib/postgresql/data

  qdrant:
    volumes:
      - ./data/qdrant:/qdrant/storage

  minio:
    volumes:
      - ./data/minio:/data

  redpanda:
    volumes:
      - ./data/redpanda:/var/lib/redpanda/data

  embeddings:
    volumes:
      - ./data/embeddings:/app/models
```

### Data Survival

Data persists across:
- ✅ `docker-compose restart` - Services restart with same data
- ✅ `docker-compose down && docker-compose up` - Data preserved
- ✅ Container recreation - Data remains in `./data/` directory
- ❌ Manual deletion of `./data/` directory - **Data will be lost!**

## Backup & Restore

### Creating Backups

Use the provided backup script to create timestamped backups:

```bash
# Basic backup (creates backups/zerodb_backup_YYYYMMDD_HHMMSS.tar.gz)
./scripts/backup-local.sh

# Custom backup directory
BACKUP_DIR=/path/to/backups ./scripts/backup-local.sh

# Custom retention period (default: 7 days)
BACKUP_RETENTION_DAYS=30 ./scripts/backup-local.sh
```

#### What Gets Backed Up

- **PostgreSQL**: Complete database dump (all tables, schemas, data)
- **Qdrant**: Vector collections and indexes
- **MinIO**: All uploaded files and buckets
- **RedPanda**: Event stream data
- **Embeddings**: BGE model cache (optional)

#### Backup Contents

Each backup is a compressed tar.gz archive containing:

```
zerodb_backup_20250112_143022/
├── postgres_dump.sql          # PostgreSQL dump
├── qdrant/                    # Qdrant data directory
├── minio/                     # MinIO data directory
├── redpanda/                  # RedPanda data directory
├── embeddings/                # Model cache
└── backup_metadata.json       # Backup information
```

### Restoring Backups

Use the restore script to restore from a previous backup:

```bash
# Interactive restore (shows list of available backups)
./scripts/restore-local.sh

# Restore specific backup
./scripts/restore-local.sh backups/zerodb_backup_20250112_143022.tar.gz
```

⚠️ **WARNING**: Restoring will **REPLACE ALL CURRENT DATA**. Make sure to backup current data first!

#### Restore Process

1. Lists available backups
2. Prompts for confirmation (type "yes" to proceed)
3. Stops all services
4. Clears existing data directories
5. Restores data from backup
6. Starts all services
7. Verifies service health

## Automated Backups

### Using Cron

Add to your crontab for automated backups:

```bash
# Edit crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * cd /path/to/zerodb-local && ./scripts/backup-local.sh >> logs/backup.log 2>&1

# Every 6 hours
0 */6 * * * cd /path/to/zerodb-local && ./scripts/backup-local.sh >> logs/backup.log 2>&1
```

### Backup Rotation

The backup script automatically deletes backups older than `BACKUP_RETENTION_DAYS` (default: 7 days).

**Retention strategies:**

| Frequency | Retention | Use Case |
|-----------|-----------|----------|
| Hourly | 24 hours | Development, frequent changes |
| Every 6 hours | 7 days | Active development |
| Daily | 30 days | Staging environments |
| Daily | 90 days | Production environments |
| Weekly | 1 year | Long-term archival |

## Data Migration

### Exporting Data to Cloud

To migrate from ZeroDB Local to ZeroDB Cloud:

```bash
# 1. Create a backup
./scripts/backup-local.sh

# 2. Use ZeroDB CLI to export
zerodb export --source local --target cloud --project-id <project-id>

# 3. Verify migration
zerodb verify --project-id <project-id>
```

See [SYNC_STRATEGY.md](./SYNC_STRATEGY.md) for detailed migration instructions.

### Importing Data from Cloud

To import data from ZeroDB Cloud to Local:

```bash
# 1. Download data from cloud
zerodb download --project-id <project-id> --output cloud-backup.tar.gz

# 2. Restore locally
./scripts/restore-local.sh cloud-backup.tar.gz
```

## Data Cleanup

### Removing Old Data

```bash
# Stop services
docker-compose down

# Delete all data (⚠️ CANNOT BE UNDONE!)
rm -rf data/

# Restart with fresh data
docker-compose up -d
```

### Selective Cleanup

```bash
# Clear only PostgreSQL data
docker-compose down postgres
rm -rf data/postgres
docker-compose up -d postgres

# Clear only vector data
rm -rf data/qdrant
docker-compose restart qdrant

# Clear only files
rm -rf data/minio/*
docker-compose restart minio
```

## Storage Optimization

### Disk Space Management

Monitor disk usage:

```bash
# Check total data size
du -sh data/

# Check size per component
du -sh data/*/

# Check available disk space
df -h .
```

### Database Optimization

#### PostgreSQL VACUUM

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U zerodb -d zerodb_local

# Run VACUUM
VACUUM ANALYZE;

# Reclaim disk space
VACUUM FULL;
```

#### Qdrant Optimization

```bash
# Optimize collections
curl -X POST http://localhost:6333/collections/zerodb_local/optimize
```

### File Storage Cleanup

Remove orphaned files from MinIO:

```bash
# List all buckets
docker-compose exec minio mc ls local/

# Remove specific bucket
docker-compose exec minio mc rb --force local/old-bucket
```

## Disaster Recovery

### Recovery Plan

**Scenario 1: Data Corruption**
1. Stop affected service: `docker-compose stop <service>`
2. Restore from latest backup: `./scripts/restore-local.sh`
3. Verify data integrity
4. Resume operations

**Scenario 2: Accidental Deletion**
1. Immediately create backup of current state
2. Restore from most recent backup before deletion
3. Manually recover missing data if possible
4. Document incident

**Scenario 3: Disk Failure**
1. Stop all services: `docker-compose down`
2. Replace/repair disk
3. Restore from offsite backup
4. Verify all services: `curl http://localhost:8000/health`

### Backup Best Practices

1. **3-2-1 Rule**:
   - **3** copies of data (original + 2 backups)
   - **2** different storage types (local + cloud)
   - **1** offsite backup (cloud storage, different server)

2. **Regular Testing**:
   - Test restore process monthly
   - Verify backup integrity
   - Document restoration time

3. **Monitoring**:
   - Track backup success/failure
   - Alert on backup failures
   - Monitor disk space

4. **Documentation**:
   - Document backup schedule
   - Maintain recovery procedures
   - Keep backup inventory

## Troubleshooting

### Backup Issues

**Problem**: Backup script fails with "Permission denied"

```bash
# Solution: Make script executable
chmod +x scripts/backup-local.sh
chmod +x scripts/restore-local.sh
```

**Problem**: Backup fails with "No space left on device"

```bash
# Solution: Clear old backups
find backups/ -name "*.tar.gz" -mtime +7 -delete

# Or move to external storage
mv backups/*.tar.gz /external/storage/
```

**Problem**: PostgreSQL dump fails

```bash
# Solution: Ensure PostgreSQL is running
docker-compose ps postgres

# Restart if needed
docker-compose restart postgres
```

### Restore Issues

**Problem**: Restore fails with "Database already exists"

```bash
# Solution: Force drop database
docker-compose exec postgres psql -U zerodb -d postgres -c "DROP DATABASE zerodb_local;"
./scripts/restore-local.sh
```

**Problem**: Services won't start after restore

```bash
# Solution: Check logs
docker-compose logs --tail=100

# Fix file permissions
sudo chown -R $(id -u):$(id -g) data/

# Restart services
docker-compose down && docker-compose up -d
```

**Problem**: Qdrant collections not restored

```bash
# Solution: Manually copy data
cp -r backups/extracted/qdrant/* data/qdrant/
docker-compose restart qdrant
```

### Data Corruption

**Problem**: PostgreSQL reports corruption

```bash
# Solution 1: Run integrity check
docker-compose exec postgres psql -U zerodb -d zerodb_local -c "SELECT pg_database.datname, pg_stat_get_db_xact_commit(pg_database.oid) FROM pg_database;"

# Solution 2: Restore from backup
./scripts/restore-local.sh

# Solution 3: Manual recovery
docker-compose exec postgres pg_resetwal /var/lib/postgresql/data
```

**Problem**: MinIO objects corrupted

```bash
# Solution: Run heal operation
docker-compose exec minio mc admin heal local/
```

## Monitoring & Alerts

### Health Checks

```bash
# Check overall health
curl http://localhost:8000/health

# Check individual services
curl http://localhost:6333/healthz           # Qdrant
curl http://localhost:9000/minio/health/live # MinIO
curl http://localhost:8001/health            # Embeddings
```

### Disk Space Monitoring

```bash
#!/bin/bash
# disk-monitor.sh - Alert on low disk space

THRESHOLD=80  # Percent full
USAGE=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')

if [ $USAGE -gt $THRESHOLD ]; then
    echo "WARNING: Disk usage at ${USAGE}%"
    # Send alert (email, Slack, etc.)
fi
```

### Backup Verification

```bash
#!/bin/bash
# verify-backup.sh - Verify latest backup integrity

LATEST_BACKUP=$(ls -t backups/*.tar.gz | head -1)

# Check file exists
if [ ! -f "$LATEST_BACKUP" ]; then
    echo "ERROR: No backup found"
    exit 1
fi

# Check file size (should be > 1MB)
SIZE=$(stat -f%z "$LATEST_BACKUP")
if [ $SIZE -lt 1048576 ]; then
    echo "ERROR: Backup too small (${SIZE} bytes)"
    exit 1
fi

# Check archive integrity
tar -tzf "$LATEST_BACKUP" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Backup archive corrupted"
    exit 1
fi

echo "✅ Backup verified: $LATEST_BACKUP"
```

## References

- Docker Volumes: https://docs.docker.com/storage/volumes/
- PostgreSQL Backup: https://www.postgresql.org/docs/current/backup.html
- Qdrant Backup: https://qdrant.tech/documentation/guides/backup/
- MinIO Backup: https://min.io/docs/minio/linux/operations/backup-restore.html
- Data Migration: [SYNC_STRATEGY.md](./SYNC_STRATEGY.md)
- Environment Setup: [ENVIRONMENT_SETUP.md](./ENVIRONMENT_SETUP.md)
