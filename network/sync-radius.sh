#!/usr/bin/env bash
# ===========================================================================
# Sync active vouchers from PostgreSQL to FreeRADIUS tables.
# Run this whenever a new voucher is purchased/activated.
# ===========================================================================
set -euo pipefail

DB_NAME="${DB_NAME:-zyranet}"
DB_USER="${DB_USER:-zyranet}"

echo "Syncing active vouchers to RADIUS..."

sudo -u postgres psql -d "$DB_NAME" << 'SQL'
-- Clear old RADIUS entries
TRUNCATE radcheck;
TRUNCATE radreply;

-- Sync active vouchers → radcheck (username + password)
INSERT INTO radcheck (username, attribute, op, value)
SELECT v.code, 'Cleartext-Password', ':=', v.code
FROM vouchers v
WHERE v.status = 'active';

-- Sync active vouchers → radreply (session timeout)
INSERT INTO radreply (username, attribute, op, value)
SELECT v.code, 'Session-Timeout', '=', p.duration_seconds::text
FROM vouchers v
JOIN plans p ON v.plan_id = p.id
WHERE v.status = 'active';

-- Sync active vouchers → radreply (simultaneous-use = 1)
INSERT INTO radreply (username, attribute, op, value)
SELECT v.code, 'Simultaneous-Use', '=', '1'
FROM vouchers v
WHERE v.status = 'active';

SELECT count(*) AS synced_vouchers FROM radcheck;
SQL

# Signal FreeRADIUS to reload
sudo killall -HUP freeradius 2>/dev/null && echo "FreeRADIUS reloaded." || echo "FreeRADIUS not running, skipped reload."
echo "Done."
