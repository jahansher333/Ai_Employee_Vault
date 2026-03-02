#!/bin/bash
# Odoo database backup — daily via cron
# Usage: Add to crontab: 0 2 * * * /home/ai-employee/vault/deploy/backup/odoo-backup.sh
#
# Creates gzipped pg_dump with 7-day retention.

set -euo pipefail

BACKUP_DIR="/backups/odoo"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/odoo_${TIMESTAMP}.sql.gz"
LOG_FILE="${BACKUP_DIR}/backup.log"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting Odoo backup" >> "$LOG_FILE"

# Run pg_dump inside the postgres container
if docker exec odoo-db pg_dump -U odoo postgres 2>> "$LOG_FILE" | gzip > "$BACKUP_FILE"; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "[$(date)] Backup complete: $BACKUP_FILE ($SIZE)" >> "$LOG_FILE"
else
    echo "[$(date)] ERROR: Backup failed" >> "$LOG_FILE"
    exit 1
fi

# Clean old backups
DELETED=$(find "$BACKUP_DIR" -name "odoo_*.sql.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
    echo "[$(date)] Cleaned $DELETED old backup(s)" >> "$LOG_FILE"
fi

echo "[$(date)] Backup job complete" >> "$LOG_FILE"
