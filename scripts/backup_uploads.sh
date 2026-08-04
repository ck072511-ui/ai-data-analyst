#!/bin/bash
# ==============================================================================
# AI Data Analyst - Uploaded Datasets Backup Script
# ==============================================================================
set -e

# Configuration
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
UPLOADS_PATH="/app/data/uploads"

# Auto-detect running container
CONTAINER_NAME="ai_analyst_prod_backend"
if ! docker ps --format "{{.Names}}" | grep -q "ai_analyst_prod_backend"; then
    if docker ps --format "{{.Names}}" | grep -q "ai_analyst_backend"; then
        CONTAINER_NAME="ai_analyst_backend"
    fi
fi
BACKUP_FILE="${BACKUP_DIR}/uploads_backup_${TIMESTAMP}.tar.gz"

mkdir -p "${BACKUP_DIR}"

echo "======================================================================"
echo "Starting Uploaded Datasets Backup..."
echo "Container: ${CONTAINER_NAME}"
echo "Path:      ${UPLOADS_PATH}"
echo "Target:    ${BACKUP_FILE}"
echo "======================================================================"

# Compress uploads folder inside container, write archive to host
docker exec -t "${CONTAINER_NAME}" tar -czf - -C "${UPLOADS_PATH}" . > "${BACKUP_FILE}"

echo "----------------------------------------------------------------------"
echo "Uploads Backup Completed Successfully!"
echo "File Details:"
ls -lh "${BACKUP_FILE}"
echo "======================================================================"
