# Zyranet — Unified One-Network Deployment

## Architecture

```
                    Starlink
                       │
              ┌────────┴────────┐
              │  AX1300 Router   │  Guest portal + RADIUS client
              │  192.168.1.1     │  SSID: CET-CreativeZone (open)
              └────────┬────────┘
                       │ LAN port
              ┌────────┴────────┐
              │  Linux Mint      │  Single LAN port (192.168.1.2)
              │  Server          │
              │  ├─ FreeRADIUS   │  RADIUS server (192.168.1.2:1812)
              │  ├─ PostgreSQL   │  Voucher database
              │  ├─ FastAPI      │  Admin dashboard (192.168.1.2:8000)
              │  └─ Telegram Bot │  Voucher purchase bot
              └─────────────────┘
                       │
              ┌────────┴────────┐
              │    NanoStation    │  AP (bridge mode, same SSID)
              │    M2            │
              └─────────────────┘
```

**How it works:**
1. Guest connects to `CET-CreativeZone` on the AX1300 router or NanoStation
2. Router shows captive portal page
3. Guest enters voucher code
4. Router sends RADIUS Access-Request to Linux Mint server (192.168.1.2:1812)
5. FreeRADIUS checks voucher in PostgreSQL → Access-Accept + Session-Timeout
6. Router opens the session → guest has internet
7. When Session-Timeout expires → router closes session → guest re-authenticates

## Step 1 — Linux Mint Server Setup

### Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start Docker
sudo systemctl enable docker
sudo systemctl start docker

# Add your user to docker group (logout/login after)
sudo usermod -aG docker $USER
```

### Install FreeRADIUS + PostgreSQL (native, not Docker)

```bash
sudo apt install -y freeradius freeradius-postgresql postgresql postgresql-client
```

## Step 2 — Clone Zyranet

```bash
cd /home/$USER
git clone https://github.com/Pi-Defi-world/Zyranet.git
cd Zyranet
```

## Step 3 — Database Setup

```bash
# Create database and user
sudo -u postgres psql -c "CREATE USER zyranet WITH PASSWORD 'CHANGE_ME';"
sudo -u postgres psql -c "CREATE DATABASE zyranet OWNER zyranet;"

# Load schema
sudo -u postgres psql -d zyranet -f db/schema.sql

# Create RADIUS tables
sudo -u postgres psql -d zyranet << 'EOF'
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
EOF

# Seed plans and a test voucher
sudo -u postgres psql -d zyranet << 'EOF'
INSERT INTO plans (name, duration_seconds, price_kobo, price_currency)
VALUES ('15h', 54000, 20000, 'NGN')
ON CONFLICT DO NOTHING;

INSERT INTO vouchers (code, plan_id, status)
SELECT 'TNLV-4R97-SRXM', id, 'active' FROM plans WHERE name='15h'
ON CONFLICT (code) DO NOTHING;

-- Sync to RADIUS
INSERT INTO radcheck (username, attribute, op, value)
SELECT v.code, 'Cleartext-Password', ':=', v.code
FROM vouchers v WHERE v.status = 'active';

INSERT INTO radreply (username, attribute, op, value)
SELECT v.code, 'Session-Timeout', '=', p.duration_seconds::text
FROM vouchers v JOIN plans p ON v.plan_id = p.id
WHERE v.status = 'active';
EOF
```

## Step 4 — FreeRADIUS Config

```bash
# SQL module
sudo tee /etc/freeradius/3.0/mods-available/sql > /dev/null << 'EOF'
sql {
    dialect = "postgresql"
    driver = "rlm_sql_postgresql"
    server = "localhost"
    port = 5432
    login = "zyranet"
    password = "CHANGE_ME"
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
    $INCLUDE ${modconfdir}/sql/main/postgresql/queries.conf
}
EOF
sudo ln -sf /etc/freeradius/3.0/mods-available/sql /etc/freeradius/3.0/mods-enabled/sql

# Clients — allow the router to authenticate
sudo tee /etc/freeradius/3.0/clients.conf > /dev/null << 'EOF'
client localhost {
    ipaddr = 127.0.0.1
    secret = CHANGE_ME_TO_A_LONG_RANDOM_SECRET
}

client ax1300-router {
    ipaddr = 192.168.1.1
    secret = CHANGE_ME_TO_A_LONG_RANDOM_SECRET
}
EOF

# Virtual server
sudo tee /etc/freeradius/3.0/sites-enabled/default > /dev/null << 'EOF'
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
EOF
sudo rm -f /etc/freeradius/3.0/sites-enabled/inner-tunnel

# Test and start
sudo freeradius -X 2>/dev/null &
sleep 2
radtest TNLV-4R97-SRXM TNLV-4R97-SRXM 127.0.0.1:1812 0 CHANGE_ME_TO_A_LONG_RANDOM_SECRET
# Should show: Received Access-Accept + Session-Timeout

sudo systemctl enable freeradius
```

## Step 5 — Docker Stack (API + Bot)

```bash
cd Zyranet

# Edit .env
cp .env.example .env
nano .env
# Set: DB_PASSWORD, RADIUS_SECRET, TELEGRAM_BOT_TOKEN, ADMIN_PASSWORD

# Build and start (skip radius container — using native FreeRADIUS)
docker compose up -d db api bot
```

## Step 6 — Router Configuration (AX1300)

1. Open router admin: `http://192.168.1.1`
2. **Guest Network** settings:
   - Enable Guest Network
   - SSID: `CET-CreativeZone`
   - Security: Open (no password)
   - Guest network isolation: ON
3. **Captive Portal / Authentication**:
   - Enable: YES
   - Authentication Type: RADIUS
   - RADIUS Server IP: `192.168.1.2` (your Linux Mint server)
   - RADIUS Server Port: `1812`
   - RADIUS Shared Secret: `CHANGE_ME_TO_A_LONG_RANDOM_SECRET` (must match clients.conf)
   - Accounting Port: `1813`
4. Apply & reboot

## Step 7 — NanoStation M2 Setup

1. Reset the NanoStation (hold reset 10 seconds)
2. Connect laptop directly to NanoStation Ethernet
3. Open `https://192.168.1.20` — login `ubnt` / `ubnt`
4. **Wireless** tab:
   - SSID: `CET-CreativeZone`
   - Security: None (Open)
   - Mode: `AP`
5. **Network** tab:
   - Network Mode: `Bridge`
   - IP: DHCP
6. Apply & commit
7. Connect NanoStation Ethernet to router LAN port

## Step 8 — Test

```bash
# 1. RADIUS test
radtest TNLV-4R97-SRXM TNLV-4R97-SRXM 127.0.0.1:1812 0 CHANGE_ME_TO_A_LONG_RANDOM_SECRET
# → Access-Accept + Session-Timeout = 54000

# 2. Connect phone to CET-CreativeZone
# 3. Open browser → should see portal
# 4. Enter code: TNLV-4R97-SRXM
# 5. Should get internet

# 6. Admin dashboard: http://192.168.1.2:8000/static/admin.html
# 7. Telegram bot: @dappifybot → /buy
```

## Voucher Sync Script

When new vouchers are purchased via the Telegram bot, sync them to RADIUS:

```bash
sudo -u postgres psql -d zyranet << 'EOF'
TRUNCATE radcheck;
TRUNCATE radreply;

INSERT INTO radcheck (username, attribute, op, value)
SELECT v.code, 'Cleartext-Password', ':=', v.code
FROM vouchers v WHERE v.status = 'active';

INSERT INTO radreply (username, attribute, op, value)
SELECT v.code, 'Session-Timeout', '=', p.duration_seconds::text
FROM vouchers v JOIN plans p ON v.plan_id = p.id
WHERE v.status = 'active';
EOF

# Reload FreeRADIUS
sudo killall -HUP freeradius
```

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Portal doesn't appear | Router captive portal enabled? RADIUS IP correct? |
| Code rejected | `radtest` from server — is FreeRADIUS up? |
| No internet after auth | Router RADIUS accounting enabled? |
| Bot doesn't respond | `docker logs zyranet-bot` |
| Dashboard 404 | `docker logs zyranet-api` — is it running? |
