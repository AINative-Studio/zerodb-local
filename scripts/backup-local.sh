#!/bin/bash
#
# ZeroDB Local - Backup Script
# Creates timestamped backups of all persistent data
#

set -e  # Exit on error

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="zerodb_backup_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if docker-compose is running
check_services() {
    log_info "Checking service status..."

    if ! docker-compose ps | grep -q "Up"; then
        log_warn "No services are running. Starting services..."
        docker-compose up -d
        sleep 10
    fi
}

# Create backup directory
create_backup_dir() {
    log_info "Creating backup directory: ${BACKUP_PATH}"
    mkdir -p "${BACKUP_PATH}"
}

# Backup PostgreSQL database
backup_postgres() {
    log_info "Backing up PostgreSQL database..."

    POSTGRES_USER="${POSTGRES_USER:-zerodb}"
    POSTGRES_DB="${POSTGRES_DB:-zerodb_local}"

    docker-compose exec -T postgres pg_dump \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        --clean \
        --if-exists \
        > "${BACKUP_PATH}/postgres_dump.sql"

    if [ $? -eq 0 ]; then
        log_info "PostgreSQL backup completed"
    else
        log_error "PostgreSQL backup failed"
        return 1
    fi
}

# Backup Qdrant data
backup_qdrant() {
    log_info "Backing up Qdrant data..."

    if [ -d "./data/qdrant" ]; then
        cp -r ./data/qdrant "${BACKUP_PATH}/qdrant"
        log_info "Qdrant backup completed"
    else
        log_warn "Qdrant data directory not found, skipping..."
    fi
}

# Backup MinIO data
backup_minio() {
    log_info "Backing up MinIO data..."

    if [ -d "./data/minio" ]; then
        cp -r ./data/minio "${BACKUP_PATH}/minio"
        log_info "MinIO backup completed"
    else
        log_warn "MinIO data directory not found, skipping..."
    fi
}

# Backup RedPanda data
backup_redpanda() {
    log_info "Backing up RedPanda data..."

    if [ -d "./data/redpanda" ]; then
        cp -r ./data/redpanda "${BACKUP_PATH}/redpanda"
        log_info "RedPanda backup completed"
    else
        log_warn "RedPanda data directory not found, skipping..."
    fi
}

# Backup embeddings model cache
backup_embeddings() {
    log_info "Backing up embeddings model cache..."

    if [ -d "./data/embeddings" ]; then
        cp -r ./data/embeddings "${BACKUP_PATH}/embeddings"
        log_info "Embeddings backup completed"
    else
        log_warn "Embeddings cache not found, skipping..."
    fi
}

# Create backup metadata
create_metadata() {
    log_info "Creating backup metadata..."

    cat > "${BACKUP_PATH}/backup_metadata.json" <<EOF
{
  "timestamp": "${TIMESTAMP}",
  "backup_name": "${BACKUP_NAME}",
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "hostname": "$(hostname)",
  "components": {
    "postgres": $([ -f "${BACKUP_PATH}/postgres_dump.sql" ] && echo "true" || echo "false"),
    "qdrant": $([ -d "${BACKUP_PATH}/qdrant" ] && echo "true" || echo "false"),
    "minio": $([ -d "${BACKUP_PATH}/minio" ] && echo "true" || echo "false"),
    "redpanda": $([ -d "${BACKUP_PATH}/redpanda" ] && echo "true" || echo "false"),
    "embeddings": $([ -d "${BACKUP_PATH}/embeddings" ] && echo "true" || echo "false")
  }
}
EOF
}

# Compress backup
compress_backup() {
    log_info "Compressing backup..."

    cd "${BACKUP_DIR}"
    tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
    rm -rf "${BACKUP_NAME}"

    BACKUP_SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)
    log_info "Backup compressed to ${BACKUP_NAME}.tar.gz (${BACKUP_SIZE})"
}

# Cleanup old backups
cleanup_old_backups() {
    RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
    log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."

    find "${BACKUP_DIR}" -name "zerodb_backup_*.tar.gz" -mtime +${RETENTION_DAYS} -delete

    REMAINING_BACKUPS=$(find "${BACKUP_DIR}" -name "zerodb_backup_*.tar.gz" | wc -l)
    log_info "Remaining backups: ${REMAINING_BACKUPS}"
}

# Main backup process
main() {
    log_info "==================================================="
    log_info "ZeroDB Local Backup - ${TIMESTAMP}"
    log_info "==================================================="

    # Load environment variables if .env.local exists
    if [ -f ".env.local" ]; then
        set -a
        source .env.local
        set +a
    fi

    check_services
    create_backup_dir

    # Backup each component
    backup_postgres || log_error "PostgreSQL backup failed"
    backup_qdrant
    backup_minio
    backup_redpanda
    backup_embeddings

    create_metadata
    compress_backup
    cleanup_old_backups

    log_info "==================================================="
    log_info "Backup completed successfully!"
    log_info "Backup location: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
    log_info "==================================================="
}

# Run main function
main "$@"
