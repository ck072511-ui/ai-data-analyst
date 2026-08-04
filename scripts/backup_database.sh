#!/bin/bash
# ==============================================================================
# AI Data Analyst - PostgreSQL Backup Script
# ==============================================================================
set -e

# Configuration
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_USER="analyst"
DB_NAME="analytics_db"

# Auto-detect running container
CONTAINER_NAME="ai_analyst_prod_db"
if ! docker ps --format "{{.Names}}" | grep -q "ai_analyst_prod_db"; then
    if docker ps --format "{{.Names}}" | grep -q "ai_analyst_db"; then
        CONTAINER_NAME="ai_analyst_db"
    fi
fi
BACKUP_FILE="${BACKUP_DIR}/postgres_backup_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "======================================================================"
echo "Starting PostgreSQL Database Backup..."
echo "Container: ${CONTAINER_NAME}"
echo "Database:  ${DB_NAME}"
echo "Target:    ${BACKUP_FILE}"
echo "======================================================================"

# Execute pg_dump inside postgres container and compress to host backups dir
docker exec -t "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" "${DB_NAME}" | gzip > "${BACKUP_FILE}"

echo "----------------------------------------------------------------------"
echo "Backup Completed Successfully!"
echo "File Details:"
ls -lh "${BACKUP_FILE}"
echo "======================================================================"
