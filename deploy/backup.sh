#!/usr/bin/env bash
# Nightly encrypted PostgreSQL custom-format backup for Zyranet.
# Configure BACKUP_GPG_RECIPIENT and PostgreSQL access via a protected
# .pgpass file (or local peer auth) in the scheduler's environment.
# Install: sudo crontab -e ; add:
#   0 3 * * * BACKUP_GPG_RECIPIENT=ops-backup@example.edu /opt/zyranet/deploy/backup.sh >> /var/log/zyranet-backup.log 2>&1
set -euo pipefail

umask 077
BACKUP_DIR="${BACKUP_DIR:-/opt/zyranet/backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
DB_NAME="${DB_NAME:-zyranet}"
DB_USER="${DB_USER:-zyranet}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"
BACKUP_GPG_RECIPIENT="${BACKUP_GPG_RECIPIENT:-}"

if [[ -z "$BACKUP_GPG_RECIPIENT" ]]; then
  echo "BACKUP_GPG_RECIPIENT must name an installed GPG public-key recipient" >&2
  exit 1
fi
command -v pg_dump >/dev/null || { echo "pg_dump is required" >&2; exit 1; }
command -v pg_restore >/dev/null || { echo "pg_restore is required" >&2; exit 1; }
command -v gpg >/dev/null || { echo "gpg is required" >&2; exit 1; }

mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
FILE="$BACKUP_DIR/zyranet-$STAMP.dump.gpg"
RAW_FILE="$(mktemp "$BACKUP_DIR/.zyranet-$STAMP.XXXXXX.dump")"
ENCRYPTED_FILE="$BACKUP_DIR/.zyranet-$STAMP.$$.gpg"
trap 'rm -f "$RAW_FILE" "$ENCRYPTED_FILE"' EXIT

pg_dump --no-password --format=custom --no-owner --no-privileges \
  --host "$DB_HOST" --port "$DB_PORT" --username "$DB_USER" \
  --dbname "$DB_NAME" --file "$RAW_FILE"
pg_restore --list "$RAW_FILE" >/dev/null
gpg --batch --yes --trust-model always --recipient "$BACKUP_GPG_RECIPIENT" \
  --output "$ENCRYPTED_FILE" --encrypt "$RAW_FILE"
gpg --batch --list-packets "$ENCRYPTED_FILE" >/dev/null
chmod 0600 "$ENCRYPTED_FILE"
mv "$ENCRYPTED_FILE" "$FILE"

# Prune old encrypted backups only after a new archive is verified and stored.
find "$BACKUP_DIR" -type f -name 'zyranet-*.dump.gpg' -mtime +"$KEEP_DAYS" -delete

echo "Encrypted backup written: $FILE"
