#!/usr/bin/env bash
# Nightly Postgres backup + archive for Zyranet.
# Install: sudo crontab -e ; add:
#   0 3 * * * /opt/zyranet/deploy/backup.sh >> /var/log/zyranet-backup.log 2>&1
set -euo pipefail

BACKUP_DIR=/opt/zyranet/backups
KEEP_DAYS=14
DB_NAME="${DB_NAME:-zyranet}"
DB_USER="${DB_USER:-zyranet}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
FILE="$BACKUP_DIR/zyranet-$STAMP.sql.gz"

pg_dump -U "$DB_USER" -h localhost "$DB_NAME" | gzip > "$FILE"

# Prune old backups.
find "$BACKUP_DIR" -name 'zyranet-*.sql.gz' -mtime +"$KEEP_DAYS" -delete

echo "Backup written: $FILE"
