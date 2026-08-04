#!/bin/bash
# ==============================================================================
# AI Data Analyst - Uploaded Datasets Restore Script
# ==============================================================================
set -e

UPLOADS_PATH="/app/data/uploads"

# Auto-detect running container
CONTAINER_NAME="ai_analyst_prod_backend"
if ! docker ps --format "{{.Names}}" | grep -q "ai_analyst_prod_backend"; then
    if docker ps --format "{{.Names}}" | grep -q "ai_analyst_backend"; then
        CONTAINER_NAME="ai_analyst_backend"
    fi
fi

if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_uploads_backup.tar.gz>"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: Backup file not found at: ${BACKUP_FILE}"
    exit 1
fi

echo "======================================================================"
echo "Starting Uploaded Datasets Restore..."
echo "Container: ${CONTAINER_NAME}"
echo "Path:      ${UPLOADS_PATH}"
echo "Source:    ${BACKUP_FILE}"
echo "======================================================================"

# Send archive to container stdin and extract inside uploads path
docker exec -i "${CONTAINER_NAME}" tar -xzf - -C "${UPLOADS_PATH}" < "${BACKUP_FILE}"

echo "----------------------------------------------------------------------"
echo "Uploads Restore Completed Successfully!"
echo "======================================================================"
