#!/bin/bash
#
# ZeroDB Local - Restore Script
# Restores data from a timestamped backup
#

set -e  # Exit on error

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_prompt() {
    echo -e "${BLUE}[INPUT]${NC} $1"
}

# List available backups
list_backups() {
    log_info "Available backups:"
    echo ""

    if [ ! -d "${BACKUP_DIR}" ]; then
        log_error "Backup directory not found: ${BACKUP_DIR}"
        exit 1
    fi

    BACKUPS=($(find "${BACKUP_DIR}" -name "zerodb_backup_*.tar.gz" -type f | sort -r))

    if [ ${#BACKUPS[@]} -eq 0 ]; then
        log_error "No backups found in ${BACKUP_DIR}"
        exit 1
    fi

    for i in "${!BACKUPS[@]}"; do
        BACKUP_FILE=$(basename "${BACKUPS[$i]}")
        BACKUP_SIZE=$(du -h "${BACKUPS[$i]}" | cut -f1)
        BACKUP_DATE=$(echo "${BACKUP_FILE}" | sed 's/zerodb_backup_\([0-9]\{8\}_[0-9]\{6\}\).*/\1/' | sed 's/_/ /')

        echo "  [$((i+1))] ${BACKUP_FILE} (${BACKUP_SIZE}) - ${BACKUP_DATE}"
    done

    echo ""
}

# Select backup to restore
select_backup() {
    list_backups

    log_prompt "Enter backup number to restore (or 'q' to quit): "
    read -r SELECTION

    if [ "${SELECTION}" == "q" ]; then
        log_info "Restore cancelled"
        exit 0
    fi

    if ! [[ "${SELECTION}" =~ ^[0-9]+$ ]] || [ "${SELECTION}" -lt 1 ] || [ "${SELECTION}" -gt ${#BACKUPS[@]} ]; then
        log_error "Invalid selection"
        exit 1
    fi

    BACKUP_FILE="${BACKUPS[$((SELECTION-1))]}"
    log_info "Selected backup: $(basename ${BACKUP_FILE})"
}

# Confirm restore operation
confirm_restore() {
    log_warn "⚠️  WARNING: This will REPLACE all current data!"
    log_warn "⚠️  All existing data in PostgreSQL, Qdrant, MinIO, and RedPanda will be deleted."
    echo ""
    log_prompt "Are you sure you want to continue? (yes/no): "
    read -r CONFIRMATION

    if [ "${CONFIRMATION}" != "yes" ]; then
        log_info "Restore cancelled"
        exit 0
    fi
}

# Stop all services
stop_services() {
    log_info "Stopping all services..."
    docker-compose down
    log_info "Services stopped"
}

# Extract backup
extract_backup() {
    log_info "Extracting backup..."

    BACKUP_NAME=$(basename "${BACKUP_FILE}" .tar.gz)
    EXTRACT_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

    cd "${BACKUP_DIR}"
    tar -xzf "$(basename ${BACKUP_FILE})"

    log_info "Backup extracted to: ${EXTRACT_PATH}"
}

# Restore PostgreSQL database
restore_postgres() {
    log_info "Restoring PostgreSQL database..."

    if [ ! -f "${EXTRACT_PATH}/postgres_dump.sql" ]; then
        log_warn "PostgreSQL backup not found, skipping..."
        return
    fi

    # Start only PostgreSQL service
    docker-compose up -d postgres
    sleep 5

    POSTGRES_USER="${POSTGRES_USER:-zerodb}"
    POSTGRES_DB="${POSTGRES_DB:-zerodb_local}"

    # Drop and recreate database
    docker-compose exec -T postgres psql -U "${POSTGRES_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"
    docker-compose exec -T postgres psql -U "${POSTGRES_USER}" -d postgres -c "CREATE DATABASE ${POSTGRES_DB};"

    # Restore from backup
    docker-compose exec -T postgres psql \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        < "${EXTRACT_PATH}/postgres_dump.sql"

    log_info "PostgreSQL restored successfully"
}

# Restore Qdrant data
restore_qdrant() {
    log_info "Restoring Qdrant data..."

    if [ ! -d "${EXTRACT_PATH}/qdrant" ]; then
        log_warn "Qdrant backup not found, skipping..."
        return
    fi

    # Clear existing data
    rm -rf ./data/qdrant
    mkdir -p ./data/qdrant

    # Copy backup data
    cp -r "${EXTRACT_PATH}/qdrant"/* ./data/qdrant/

    log_info "Qdrant data restored successfully"
}

# Restore MinIO data
restore_minio() {
    log_info "Restoring MinIO data..."

    if [ ! -d "${EXTRACT_PATH}/minio" ]; then
        log_warn "MinIO backup not found, skipping..."
        return
    fi

    # Clear existing data
    rm -rf ./data/minio
    mkdir -p ./data/minio

    # Copy backup data
    cp -r "${EXTRACT_PATH}/minio"/* ./data/minio/

    log_info "MinIO data restored successfully"
}

# Restore RedPanda data
restore_redpanda() {
    log_info "Restoring RedPanda data..."

    if [ ! -d "${EXTRACT_PATH}/redpanda" ]; then
        log_warn "RedPanda backup not found, skipping..."
        return
    fi

    # Clear existing data
    rm -rf ./data/redpanda
    mkdir -p ./data/redpanda

    # Copy backup data
    cp -r "${EXTRACT_PATH}/redpanda"/* ./data/redpanda/

    log_info "RedPanda data restored successfully"
}

# Restore embeddings cache
restore_embeddings() {
    log_info "Restoring embeddings cache..."

    if [ ! -d "${EXTRACT_PATH}/embeddings" ]; then
        log_warn "Embeddings backup not found, skipping..."
        return
    fi

    # Clear existing cache
    rm -rf ./data/embeddings
    mkdir -p ./data/embeddings

    # Copy backup data
    cp -r "${EXTRACT_PATH}/embeddings"/* ./data/embeddings/

    log_info "Embeddings cache restored successfully"
}

# Start all services
start_services() {
    log_info "Starting all services..."
    docker-compose up -d
    sleep 10

    log_info "Waiting for services to become healthy..."
    sleep 5

    # Check health
    docker-compose ps
}

# Cleanup extracted backup
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -rf "${EXTRACT_PATH}"
    log_info "Cleanup completed"
}

# Display restore summary
show_summary() {
    log_info "==================================================="
    log_info "Restore Summary"
    log_info "==================================================="

    if [ -f "${EXTRACT_PATH}/backup_metadata.json" ]; then
        cat "${EXTRACT_PATH}/backup_metadata.json"
    fi

    log_info "==================================================="
    log_info "Restore completed successfully!"
    log_info "==================================================="
}

# Main restore process
main() {
    log_info "==================================================="
    log_info "ZeroDB Local Restore"
    log_info "==================================================="

    # Load environment variables if .env.local exists
    if [ -f ".env.local" ]; then
        set -a
        source .env.local
        set +a
    fi

    # Select backup file
    if [ -z "$1" ]; then
        select_backup
    else
        BACKUP_FILE="$1"
        if [ ! -f "${BACKUP_FILE}" ]; then
            log_error "Backup file not found: ${BACKUP_FILE}"
            exit 1
        fi
    fi

    confirm_restore
    stop_services
    extract_backup

    # Restore each component
    restore_postgres
    restore_qdrant
    restore_minio
    restore_redpanda
    restore_embeddings

    start_services
    show_summary
    cleanup

    log_info "==================================================="
    log_info "All services restored and running"
    log_info "Verify with: docker-compose ps"
    log_info "Check health: curl http://localhost:8000/health"
    log_info "==================================================="
}

# Run main function
main "$@"
