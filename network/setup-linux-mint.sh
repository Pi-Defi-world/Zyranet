#!/bin/bash
set -e

# ===========================================================================
# Zyranet Linux Mint Server Setup
#
# Run this on a fresh Linux Mint machine:
#   git clone https://github.com/Pi-Defi-world/Zyranet.git
#   cd Zyranet
#   sudo bash network/setup-linux-mint.sh
#
# Prerequisites:
#   - Linux Mint installed and running
#   - Ethernet cable from server to AX1300 router LAN port
#   - Internet access on the server
# ===========================================================================

echo "========================================="
echo " Zyranet Server Setup"
echo "========================================="

# Collect configuration
read -p "Server IP (default 192.168.1.2): " SERVER_IP
SERVER_IP=${SERVER_IP:-192.168.1.2}

read -p "DB password (default: changeme123): " DB_PASS
DB_PASS=${DB_PASS:-changeme123}

read -p "RADIUS shared secret: " RADIUS_SECRET
RADIUS_SECRET=${RADIUS_SECRET:-$(openssl rand -hex 32)}

read -p "Telegram bot token: " TG_TOKEN

read -p "Admin password (default: admin123): " ADMIN_PASS
ADMIN_PASS=${ADMIN_PASS:-admin123}

ADMIN_JWT=$(openssl rand -hex 32)

echo ""
echo "Installing packages..."

# Docker
if ! command -v docker &>/dev/null; then
    sudo apt update
    sudo apt install -y ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo systemctl enable docker
    sudo systemctl start docker
    sudo usermod -aG docker $USER
    echo "Docker installed. Log out and back in for group changes."
fi

# FreeRADIUS + PostgreSQL
sudo apt install -y freeradius freeradius-postgresql postgresql postgresql-client net-tools

echo ""
echo "Configuring PostgreSQL..."

# Database
sudo -u postgres psql -c "CREATE USER zyranet WITH PASSWORD '${DB_PASS}';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE zyranet OWNER zyranet;" 2>/dev/null || true
sudo -u postgres psql -d zyranet -f db/schema.sql

# RADIUS tables
sudo -u postgres psql -d zyranet << SQLEOF
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

# Seed plans + test voucher + sync to RADIUS
sudo -u postgres psql -d zyranet << SQLEOF
INSERT INTO plans (name, duration_seconds, price_kobo, price_currency)
VALUES ('15h', 54000, 20000, 'NGN')
ON CONFLICT DO NOTHING;

INSERT INTO vouchers (code, plan_id, status)
SELECT 'TNLV-4R97-SRXM', id, 'active' FROM plans WHERE name='15h'
ON CONFLICT (code) DO NOTHING;

INSERT INTO radcheck (username, attribute, op, value)
SELECT v.code, 'Cleartext-Password', ':=', v.code
FROM vouchers v WHERE v.status = 'active';

INSERT INTO radreply (username, attribute, op, value)
SELECT v.code, 'Session-Timeout', '=', p.duration_seconds::text
FROM vouchers v JOIN plans p ON v.plan_id = p.id
WHERE v.status = 'active';
SQLEOF

echo ""
echo "Configuring FreeRADIUS..."

# SQL module
sudo tee /etc/freeradius/3.0/mods-available/sql > /dev/null << RADIUSEOF
sql {
    dialect = "postgresql"
    driver = "rlm_sql_postgresql"
    server = "localhost"
    port = 5432
    login = "zyranet"
    password = "${DB_PASS}"
    radius_db = "zyranet"
    read_clients = no
    acct_table1 = "radacct"
    acct_table2 = "radacct"
    postauth_table = "radpostauth"
    authcheck_table = "radcheck"
    groupcheck_table = "radgroupcheck"
    authreply_table = "radreply"
    groupreply_table = "radgroupreply"
    usergroup_table = "radusergroup"
    client_table = "nas"
    group_attribute = "SQL-Group"
    \$INCLUDE \${modconfdir}/sql/main/postgresql/queries.conf
}
RADIUSEOF
sudo ln -sf /etc/freeradius/3.0/mods-available/sql /etc/freeradius/3.0/mods-enabled/sql

# Clients
sudo tee /etc/freeradius/3.0/clients.conf > /dev/null << RADIUSEOF
client localhost {
    ipaddr = 127.0.0.1
    secret = ${RADIUS_SECRET}
}

client ax1300-router {
    ipaddr = 192.168.1.1
    secret = ${RADIUS_SECRET}
}
RADIUSEOF

# Virtual server
sudo tee /etc/freeradius/3.0/sites-enabled/default > /dev/null << RADIUSEOF
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
        eap { ok = return }
        sql
        pap
    }
    authenticate {
        Auth-Type PAP { pap }
        Auth-Type CHAP { chap }
        Auth-Type MS-CHAP { mschap }
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
        update { &reply: += &session-state: }
        sql
    }
}
RADIUSEOF
sudo rm -f /etc/freeradius/3.0/sites-enabled/inner-tunnel

# Set server IP
sudo nmcli con mod "Wired connection 1" ipv4.addresses "${SERVER_IP}/24" ipv4.method manual
sudo nmcli con up "Wired connection 1" 2>/dev/null || true

# Write .env
cp .env.example .env
sed -i "s/DB_PASSWORD=CHANGE_ME/DB_PASSWORD=${DB_PASS}/" .env
sed -i "s/RADIUS_SECRET=CHANGE_ME_TO_A_LONG_RANDOM_SECRET/RADIUS_SECRET=${RADIUS_SECRET}/" .env
sed -i "s/ADMIN_JWT_SECRET=CHANGE_ME_TO_A_LONG_RANDOM_SECRET/ADMIN_JWT_SECRET=${ADMIN_JWT}/" .env
sed -i "s/ADMIN_PASSWORD=CHANGE_ME/ADMIN_PASSWORD=${ADMIN_PASS}/" .env
sed -i "s|DB_URL=postgresql+asyncpg://zyranet:CHANGE_ME@127.0.0.1:5432/zyranet|DB_URL=postgresql+asyncpg://zyranet:${DB_PASS}@127.0.0.1:5432/zyranet|" .env
sed -i "s|PUBLIC_BASE_URL=http://192.168.1.2:8000|PUBLIC_BASE_URL=http://${SERVER_IP}:8000|" .env
if [ -n "$TG_TOKEN" ]; then
    sed -i "s/TELEGRAM_BOT_TOKEN=.*/TELEGRAM_BOT_TOKEN=${TG_TOKEN}/" .env
fi

echo ""
echo "Starting services..."

# Start FreeRADIUS
sudo systemctl enable freeradius
sudo systemctl restart freeradius
sleep 2

# Test RADIUS
echo "Testing RADIUS..."
radtest TNLV-4R97-SRXM TNLV-4R97-SRXM 127.0.0.1:1812 0 "${RADIUS_SECRET}" 2>&1

echo ""
echo "Starting Docker containers..."
docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo "========================================="
echo " Setup Complete!"
echo "========================================="
echo ""
echo " Server IP:     ${SERVER_IP}"
echo " RADIUS Secret: ${RADIUS_SECRET}"
echo " Admin Panel:   http://${SERVER_IP}:8000/static/admin.html"
echo " Voucher Code:  TNLV-4R97-SRXM"
echo ""
echo " Next steps:"
echo " 1. On the AX1300 router, enable Guest Network + Captive Portal"
echo " 2. Set RADIUS server to ${SERVER_IP}:1812"
echo " 3. Set RADIUS secret to: ${RADIUS_SECRET}"
echo " 4. Connect your phone to CET-CreativeZone"
echo " 5. Enter the voucher code in the portal"
echo ""
