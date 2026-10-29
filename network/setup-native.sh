#!/bin/bash
set -e

echo "=== Setting up PostgreSQL ==="
su - postgres -c "psql -c \"CREATE USER zyranet WITH PASSWORD 'change-me';\"" 2>/dev/null || true
su - postgres -c "psql -c \"CREATE DATABASE zyranet OWNER zyranet;\"" 2>/dev/null || true
su - postgres -c "psql -d zyranet -f /mnt/c/Users/CET_COEAN/school-administrative-system/Zyranet/db/schema.sql" 2>&1 | tail -5

echo "=== Creating voucher ==="
su - postgres -c "psql -d zyranet -c \"INSERT INTO plans (name, duration_hours, price_cents, currency) VALUES ('15h', 15, 20000, 'NGN') ON CONFLICT DO NOTHING;\"" 2>&1
su - postgres -c "psql -d zyranet -c \"INSERT INTO vouchers (code, plan_id, status, created_at) SELECT 'TNLV-4R97-SRXM', id, 'active', NOW() FROM plans WHERE name='15h' ON CONFLICT (code) DO NOTHING;\"" 2>&1

echo "=== Configuring FreeRADIUS ==="
# Configure SQL module
cat > /etc/freeradius/3.0/mods-available/sql << 'SQLEOF'
sql {
    driver = "rlm_sql_postgresql"
    server = "localhost"
    port = 5432
    login = "zyranet"
    password = "change-me"
    radius_db = "zyranet"
    read_clients = yes
    accounting {
        reference = "current-timestamp"
        table {
            reply = radreply
            acnt = radacct
        }
    }
    post-auth {
        reference = ".query"
        query_cleanup {
            reference = "cleanup"
        }
    }
}
SQLEOF
ln -sf /etc/freeradius/3.0/mods-available/sql /etc/freeradius/3.0/mods-enabled/sql 2>/dev/null || true

# Configure clients
cat > /etc/freeradius/3.0/clients.conf << 'CLIEOF'
client localhost {
    ipaddr = 127.0.0.1
    secret = change-me-to-a-long-random-secret
}

client chilli-gateway {
    ipaddr = 172.16.30.1
    secret = change-me-to-a-long-random-secret
}
CLIEOF

# Configure default virtual server to use SQL
cat > /etc/freeradius/3.0/sites-enabled/default << 'SITEEOF'
server default {
    listen {
        type = auth
        ipaddr = *
        port = 1812
    }
    listen {
        type = acct
        ipaddr = *
        port = 1813
    }
    authorize {
        chap
        mschap
        suffix
        eap {
            ok = return
        }
        sql
        pap
    }
    authenticate {
        Auth-Type PAP {
            pap
        }
        Auth-Type CHAP {
            chap
        }
        Auth-Type MS-CHAP {
            mschap
        }
        eap
    }
    preacct {
        preprocess
        acct_unique
        suffix
    }
    accounting {
        detail
        sql
    }
    post-auth {
        update {
            &reply: += &session-state:
        }
        sql
        exec
    }
}
SITEEOF

# Ensure radcheck table has proper schema for RADIUS
su - postgres -c "psql -d zyranet -c \"
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
    groupname VARCHAR(64) NOT NULL DEFAULT '',
    realm VARCHAR(64) NOT NULL DEFAULT '',
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
    acctoutputoctets BIGINT),
    calledstationid VARCHAR(50),
    callingstationid VARCHAR(50),
    acctterminatecause VARCHAR(32),
    servicetype VARCHAR(32),
    framedprotocol VARCHAR(32),
    framedipaddress VARCHAR(15),
    framedipv6address VARCHAR(45),
    framedipv6prefix VARCHAR(45),
    framedinterfaceid VARCHAR(44),
    framedmode VARCHAR(3),
    framedmtu INT,
    framedrouting VARCHAR(64),
    filterid VARCHAR(10),
    nasidentifier VARCHAR(64),
    nasport VARCHAR(32),
    servicetype VARCHAR(32),
    xnasportid VARCHAR(32),
    xnasporttype VARCHAR(32)
);
CREATE INDEX IF NOT EXISTS idx_radacct_username ON radacct (username);
CREATE INDEX IF NOT EXISTS idx_radacct_session ON radacct (acctsessionid);
\" 2>&1 | tail -5"

echo "=== Starting FreeRADIUS ==="
freeradius -X 2>/dev/null &
sleep 2

echo "=== Testing RADIUS ==="
radtest TNLV-4R97-SRXM TNLV-4R97-SRXM 127.0.0.1:1812 0 change-me-to-a-long-random-secret 2>&1 | tail -5

echo "=== Done ==="
