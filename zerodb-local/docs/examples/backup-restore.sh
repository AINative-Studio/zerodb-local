#!/bin/bash

# Backup and Restore Example - ZeroDB Local
# This script demonstrates backup and restore operations
# Updated: 2025-12-29

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="zerodb_backup_${DATE}"

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

echo "============================================"
echo "ZeroDB Local - Backup and Restore Example"
echo "============================================"
echo ""

# ============================================================
# BACKUP OPERATIONS
# ============================================================

print_section "📦 BACKUP OPERATIONS"

echo "Step 1: Create backup directory..."
mkdir -p "${BACKUP_DIR}"
echo -e "${GREEN}✓ Backup directory ready: ${BACKUP_DIR}${NC}"

echo ""
echo "Step 2: Check if services are running..."
if ! docker ps | grep -q "zerodb-postgres"; then
    echo -e "${YELLOW}! Services not running, starting them...${NC}"
    zerodb local up
    sleep 30
else
    echo -e "${GREEN}✓ Services running${NC}"
fi

echo ""
echo "Step 3: Backup PostgreSQL database..."
echo "Creating SQL dump..."
docker exec zerodb-postgres pg_dump -U zerodb zerodb_local > "${BACKUP_DIR}/${BACKUP_NAME}.sql"
echo -e "${GREEN}✓ PostgreSQL backup created: ${BACKUP_NAME}.sql${NC}"

echo ""
echo "Step 4: Backup Qdrant vector collections..."
echo "Exporting vector collections..."
docker exec zerodb-qdrant /bin/sh -c 'tar -czf /tmp/qdrant_backup.tar.gz /qdrant/storage' 2>/dev/null || true
docker cp zerodb-qdrant:/tmp/qdrant_backup.tar.gz "${BACKUP_DIR}/${BACKUP_NAME}_qdrant.tar.gz" 2>/dev/null || true
if [ -f "${BACKUP_DIR}/${BACKUP_NAME}_qdrant.tar.gz" ]; then
    echo -e "${GREEN}✓ Qdrant backup created: ${BACKUP_NAME}_qdrant.tar.gz${NC}"
else
    echo -e "${YELLOW}! Qdrant backup skipped (no collections)${NC}"
fi

echo ""
echo "Step 5: Backup MinIO object storage..."
echo "Exporting object storage..."
docker exec zerodb-minio /bin/sh -c 'tar -czf /tmp/minio_backup.tar.gz /data' 2>/dev/null || true
docker cp zerodb-minio:/tmp/minio_backup.tar.gz "${BACKUP_DIR}/${BACKUP_NAME}_minio.tar.gz" 2>/dev/null || true
if [ -f "${BACKUP_DIR}/${BACKUP_NAME}_minio.tar.gz" ]; then
    echo -e "${GREEN}✓ MinIO backup created: ${BACKUP_NAME}_minio.tar.gz${NC}"
else
    echo -e "${YELLOW}! MinIO backup skipped (no files)${NC}"
fi

echo ""
echo "Step 6: Create backup manifest..."
cat > "${BACKUP_DIR}/${BACKUP_NAME}_manifest.txt" << EOF
ZeroDB Local Backup Manifest
============================
Backup Date: $(date)
Backup Name: ${BACKUP_NAME}

Components:
- PostgreSQL: ${BACKUP_NAME}.sql
- Qdrant: ${BACKUP_NAME}_qdrant.tar.gz
- MinIO: ${BACKUP_NAME}_minio.tar.gz

Services Status:
$(docker ps --filter name=zerodb --format "table {{.Names}}\t{{.Status}}")

Project Summary:
$(zerodb inspect projects 2>/dev/null || echo "Unable to fetch projects")
EOF
echo -e "${GREEN}✓ Manifest created: ${BACKUP_NAME}_manifest.txt${NC}"

echo ""
echo "Step 7: Calculate backup size..."
BACKUP_SIZE=$(du -sh "${BACKUP_DIR}/${BACKUP_NAME}"* | awk '{s+=$1} END {print s}')
echo -e "${GREEN}✓ Total backup size: ${BACKUP_SIZE}${NC}"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ BACKUP COMPLETE!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Backup files created in: ${BACKUP_DIR}/"
ls -lh "${BACKUP_DIR}/${BACKUP_NAME}"*
echo ""

# ============================================================
# RESTORE DEMONSTRATION
# ============================================================

print_section "♻️  RESTORE OPERATIONS"

echo "This section demonstrates how to restore from a backup."
echo -e "${YELLOW}WARNING: Restore will overwrite current data!${NC}"
echo ""

# List available backups
echo "Available backups:"
if [ -n "$(ls -A ${BACKUP_DIR}/*.sql 2>/dev/null)" ]; then
    ls -lh "${BACKUP_DIR}"/*.sql | awk '{print "  " $9 " (" $5 ")"}'
else
    echo "  No backups found"
fi
echo ""

echo -e "${YELLOW}Would you like to test restore? [y/N]${NC}"
read -r response

if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    # Find latest backup
    LATEST_BACKUP=$(ls -t "${BACKUP_DIR}"/*.sql | head -1)
    BACKUP_BASE=$(basename "$LATEST_BACKUP" .sql)

    echo ""
    echo "Restoring from: ${LATEST_BACKUP}"
    echo ""

    echo "Step 1: Stop services..."
    zerodb local down
    echo -e "${GREEN}✓ Services stopped${NC}"

    echo ""
    echo "Step 2: Start PostgreSQL only..."
    docker compose up -d postgres
    sleep 10
    echo -e "${GREEN}✓ PostgreSQL started${NC}"

    echo ""
    echo "Step 3: Drop and recreate database..."
    docker exec zerodb-postgres psql -U zerodb -c "DROP DATABASE IF EXISTS zerodb_local;" 2>/dev/null || true
    docker exec zerodb-postgres psql -U zerodb -c "CREATE DATABASE zerodb_local;"
    echo -e "${GREEN}✓ Database recreated${NC}"

    echo ""
    echo "Step 4: Restore PostgreSQL data..."
    docker exec -i zerodb-postgres psql -U zerodb zerodb_local < "${LATEST_BACKUP}"
    echo -e "${GREEN}✓ PostgreSQL data restored${NC}"

    echo ""
    echo "Step 5: Restore Qdrant collections..."
    if [ -f "${BACKUP_DIR}/${BACKUP_BASE}_qdrant.tar.gz" ]; then
        docker compose up -d qdrant
        sleep 5
        docker cp "${BACKUP_DIR}/${BACKUP_BASE}_qdrant.tar.gz" zerodb-qdrant:/tmp/qdrant_backup.tar.gz
        docker exec zerodb-qdrant /bin/sh -c 'tar -xzf /tmp/qdrant_backup.tar.gz -C /'
        echo -e "${GREEN}✓ Qdrant collections restored${NC}"
    else
        echo -e "${YELLOW}! No Qdrant backup found${NC}"
    fi

    echo ""
    echo "Step 6: Restore MinIO files..."
    if [ -f "${BACKUP_DIR}/${BACKUP_BASE}_minio.tar.gz" ]; then
        docker compose up -d minio
        sleep 5
        docker cp "${BACKUP_DIR}/${BACKUP_BASE}_minio.tar.gz" zerodb-minio:/tmp/minio_backup.tar.gz
        docker exec zerodb-minio /bin/sh -c 'tar -xzf /tmp/minio_backup.tar.gz -C /'
        echo -e "${GREEN}✓ MinIO files restored${NC}"
    else
        echo -e "${YELLOW}! No MinIO backup found${NC}"
    fi

    echo ""
    echo "Step 7: Start all services..."
    zerodb local up
    sleep 30
    echo -e "${GREEN}✓ All services started${NC}"

    echo ""
    echo "Step 8: Verify restoration..."
    zerodb inspect health
    echo ""
    zerodb inspect projects

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ RESTORE COMPLETE!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
else
    echo "Restore demonstration skipped."
fi

# ============================================================
# BACKUP MANAGEMENT
# ============================================================

print_section "🗄️  BACKUP MANAGEMENT"

echo "Step 1: List all backups..."
if [ -n "$(ls -A ${BACKUP_DIR}/*.sql 2>/dev/null)" ]; then
    echo ""
    echo "Available backups:"
    ls -lht "${BACKUP_DIR}"/*.sql | head -5 | awk '{print "  " $9 " - " $5 " - " $6 " " $7 " " $8}'

    BACKUP_COUNT=$(ls -1 "${BACKUP_DIR}"/*.sql | wc -l)
    echo ""
    echo "Total backups: ${BACKUP_COUNT}"
else
    echo "No backups found"
fi

echo ""
echo "Step 2: Calculate total backup size..."
if [ -d "${BACKUP_DIR}" ]; then
    TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" | awk '{print $1}')
    echo "Total backup storage used: ${TOTAL_SIZE}"
fi

echo ""
echo "Step 3: Cleanup old backups (keep last 7)..."
echo -e "${YELLOW}Would you like to clean up old backups? [y/N]${NC}"
read -r response

if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    # Keep only last 7 backups
    ls -t "${BACKUP_DIR}"/*.sql | tail -n +8 | while read -r backup; do
        BACKUP_BASE=$(basename "$backup" .sql)
        echo "Deleting old backup: ${BACKUP_BASE}"
        rm -f "${BACKUP_DIR}/${BACKUP_BASE}"*
    done
    echo -e "${GREEN}✓ Old backups cleaned up${NC}"
else
    echo "Cleanup skipped."
fi

# ============================================================
# SUMMARY AND RECOMMENDATIONS
# ============================================================

print_section "📋 SUMMARY AND RECOMMENDATIONS"

echo "Backup Strategy Recommendations:"
echo ""
echo "1. Daily Backups:"
echo "   - Schedule automatic backups via cron"
echo "   - Keep last 7 daily backups"
echo "   Command: 0 2 * * * /path/to/backup-local.sh"
echo ""
echo "2. Before Major Changes:"
echo "   - Always backup before sync operations"
echo "   - Always backup before upgrades"
echo "   - Always backup before schema changes"
echo ""
echo "3. Off-site Storage:"
echo "   - Copy backups to cloud storage (S3, Google Cloud)"
echo "   - Use rsync to remote servers"
echo "   - Enable ZeroDB Cloud sync as additional backup"
echo ""
echo "4. Backup Testing:"
echo "   - Test restore procedure monthly"
echo "   - Verify backup integrity regularly"
echo "   - Document restore procedures"
echo ""
echo "5. Retention Policy:"
echo "   - Daily: Keep 7 days"
echo "   - Weekly: Keep 4 weeks"
echo "   - Monthly: Keep 12 months"
echo "   - Annual: Keep indefinitely"
echo ""

echo "Quick Reference Commands:"
echo ""
echo "  Create backup:"
echo "    ./docs/examples/backup-restore.sh"
echo ""
echo "  Manual PostgreSQL backup:"
echo "    docker exec zerodb-postgres pg_dump -U zerodb zerodb_local > backup.sql"
echo ""
echo "  Manual restore:"
echo "    docker exec -i zerodb-postgres psql -U zerodb zerodb_local < backup.sql"
echo ""
echo "  List backups:"
echo "    ls -lh ${BACKUP_DIR}/"
echo ""
echo "  Verify backup:"
echo "    pg_restore --list backup.sql"
echo ""

echo "============================================"
echo "Backup and Restore Example Complete!"
echo "============================================"
echo ""
