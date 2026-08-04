#!/bin/bash
# ==============================================================================
# AI Data Analyst - PostgreSQL Restore Script
# ==============================================================================
set -e

DB_USER="analyst"
DB_NAME="analytics_db"

# Auto-detect running container
CONTAINER_NAME="ai_analyst_prod_db"
if ! docker ps --format "{{.Names}}" | grep -q "ai_analyst_prod_db"; then
    if docker ps --format "{{.Names}}" | grep -q "ai_analyst_db"; then
        CONTAINER_NAME="ai_analyst_db"
    fi
fi

if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_backup_file.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: Backup file not found at: ${BACKUP_FILE}"
    exit 1
fi

echo "======================================================================"
echo "Starting PostgreSQL Database Restore..."
echo "Container: ${CONTAINER_NAME}"
echo "Database:  ${DB_NAME}"
echo "Source:    ${BACKUP_FILE}"
echo "======================================================================"

# Read backup, decompress, and pipe to psql inside target container
gunzip -c "${BACKUP_FILE}" | docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}"

echo "----------------------------------------------------------------------"
echo "Database Restore Completed Successfully!"
echo "======================================================================"
