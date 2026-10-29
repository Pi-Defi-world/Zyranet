#!/bin/bash
set -e

echo "=== PostgreSQL ==="
su postgres -c 'psql -c "CREATE USER zyranet WITH PASSWORD '"'"'change-me'"'"';"' 2>/dev/null || true
su postgres -c 'psql -c "CREATE DATABASE zyranet OWNER zyranet;"' 2>/dev/null || true
su postgres -c 'psql -d zyranet -c "SELECT 1;"' 2>&1 | head -3

echo "=== Schema ==="
cp /mnt/c/Users/CET_COEAN/school-administrative-system/Zyranet/db/schema.sql /tmp/schema.sql
su postgres -c 'psql -d zyranet -f /tmp/schema.sql' 2>&1 | tail -3

echo "=== RADIUS tables ==="
su postgres -c 'psql -d zyranet' << 'SQLEOF'
CREATE TABLE IF NOT EXISTS radcheck (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL DEFAULT '',
    attribute VARCHAR(64) NOT NULL DEFAULT '',
    op VARCHAR(2) NOT NULL DEFAULT ':=',
    value VARCHAR(253) NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_radcheck_username ON radcheck (username);

CREATE TABLE IF NOT EXISTS radreply (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL DEFAULT '',
    attribute VARCHAR(64) NOT NULL DEFAULT '',
    op VARCHAR(2) NOT NULL DEFAULT '=',
    value VARCHAR(253) NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_radreply_username ON radreply (username);

CREATE TABLE IF NOT EXISTS radacct (
    radacctid BIGSERIAL PRIMARY KEY,
    acctsessionid VARCHAR(64) NOT NULL DEFAULT '',
    acctuniqueid VARCHAR(32) NOT NULL DEFAULT '',
    username VARCHAR(64) NOT NULL DEFAULT '',
    nasipaddress VARCHAR(15) NOT NULL DEFAULT '',
    nasportid VARCHAR(32),
    nasporttype VARCHAR(32),
    acctstarttime TIMESTAMP,
    acctstoptime TIMESTAMP,
    acctsessiontime INT,
    acctauthentic VARCHAR(32),
    connectinfo_start VARCHAR(50),
    connectinfo_stop VARCHAR(50),
    acctinputoctets BIGINT,
    acctoutputoctets BIGINT,
    calledstationid VARCHAR(50),
    callingstationid VARCHAR(50),
    acctterminatecause VARCHAR(32),
    servicetype VARCHAR(32),
    framedprotocol VARCHAR(32),
    framedipaddress VARCHAR(15)
);
CREATE INDEX IF NOT EXISTS idx_radacct_username ON radacct (username);
CREATE INDEX IF NOT EXISTS idx_radacct_session ON radacct (acctsessionid);
SQLEOF

echo "=== Voucher ==="
su postgres -c "psql -d zyranet -c \"INSERT INTO plans (name, duration_hours, price_cents, currency) VALUES ('15h', 15, 20000, 'NGN') ON CONFLICT DO NOTHING;\"" 2>&1 | head -1
su postgres -c "psql -d zyranet -c \"INSERT INTO vouchers (code, plan_id, status, created_at) SELECT 'TNLV-4R97-SRXM', id, 'active', NOW() FROM plans WHERE name='15h' ON CONFLICT (code) DO NOTHING;\"" 2>&1 | head -1

echo "=== Done ==="
