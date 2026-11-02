-- ============================================================================
-- Zyranet PostgreSQL schema
-- Business tables (app-owned) + FreeRADIUS operational tables (standard names
-- so rlm_sql works out of the box).
--
-- Money is stored as INTEGER kobo/cent to avoid float errors.
-- Vouchers are one-time, single-user (max_devices=1), 15h / weekly / monthly.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- Business: plans
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS plans (
    id                BIGSERIAL PRIMARY KEY,
    name              TEXT        NOT NULL UNIQUE,        -- "15h", "Weekly", "Monthly"
    duration_seconds  INTEGER     NOT NULL,               -- 15h = 54000
    price_kobo        INTEGER     NOT NULL,
    price_currency    TEXT        NOT NULL DEFAULT 'NGN',
    active            BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- Business: users (unique account per buyer)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id                     BIGSERIAL PRIMARY KEY,
    telegram_id            BIGINT UNIQUE,
    telegram_username      TEXT,
    telegram_name          TEXT,
    phone                  TEXT,
    flutterwave_customer_id TEXT,
    paystack_customer_id   TEXT,
    is_staff               BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- Business: vouchers
-- ----------------------------------------------------------------------------
CREATE TYPE voucher_status AS ENUM ('unused','active','expired','revoked');

CREATE TABLE IF NOT EXISTS vouchers (
    id              BIGSERIAL PRIMARY KEY,
    code            TEXT        NOT NULL UNIQUE,
    plan_id         BIGINT      NOT NULL REFERENCES plans(id),
    user_id         BIGINT      REFERENCES users(id),
    valid_from      TIMESTAMPTZ,
    valid_until     TIMESTAMPTZ,
    status          voucher_status NOT NULL DEFAULT 'unused',
    max_devices     INTEGER     NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_at         TIMESTAMPTZ,
    revoked_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_vouchers_code   ON vouchers(code);
CREATE INDEX IF NOT EXISTS idx_vouchers_user   ON vouchers(user_id);
CREATE INDEX IF NOT EXISTS idx_vouchers_status ON vouchers(status);

-- ----------------------------------------------------------------------------
-- Business: transactions (Flutterwave | Paystack)
-- ----------------------------------------------------------------------------
CREATE TYPE txn_status AS ENUM ('pending','paid','failed');
CREATE TYPE txn_provider AS ENUM ('flutterwave','paystack');

CREATE TABLE IF NOT EXISTS transactions (
    id             BIGSERIAL PRIMARY KEY,
    voucher_id     BIGINT      NOT NULL REFERENCES vouchers(id),
    user_id        BIGINT      REFERENCES users(id),
    provider       txn_provider NOT NULL,
    provider_ref   TEXT        UNIQUE,                -- provider's unique reference
    amount_kobo    INTEGER     NOT NULL,
    currency       TEXT        NOT NULL DEFAULT 'NGN',
    status         txn_status  NOT NULL DEFAULT 'pending',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    paid_at        TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_txn_user     ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_txn_voucher  ON transactions(voucher_id);
CREATE INDEX IF NOT EXISTS idx_txn_prov_ref ON transactions(provider_ref);

-- ----------------------------------------------------------------------------
-- Business: redeemed_devices (enforces Simultaneous-Use = 1)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS redeemed_devices (
    id           BIGSERIAL PRIMARY KEY,
    voucher_id   BIGINT      NOT NULL REFERENCES vouchers(id),
    mac_address  TEXT        NOT NULL,
    first_seen   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (voucher_id, mac_address)
);
CREATE INDEX IF NOT EXISTS idx_rd_voucher ON redeemed_devices(voucher_id);

-- ----------------------------------------------------------------------------
-- Business: otp_codes (SMS fallback) -- optional; used if phone-gating enabled
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS otp_codes (
    id         BIGSERIAL PRIMARY KEY,
    phone      TEXT        NOT NULL,
    code       TEXT        NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed   BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_otp_phone ON otp_codes(phone);

-- ----------------------------------------------------------------------------
-- FreeRADIUS operational tables (standard, expected by rlm_sql)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS radcheck (
    id        BIGSERIAL PRIMARY KEY,
    username  TEXT NOT NULL DEFAULT '',
    attribute TEXT NOT NULL DEFAULT '',
    op        VARCHAR(2) NOT NULL DEFAULT '==',
    value     TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_radcheck_username ON radcheck(username);

CREATE TABLE IF NOT EXISTS radreply (
    id        BIGSERIAL PRIMARY KEY,
    username  TEXT NOT NULL DEFAULT '',
    attribute TEXT NOT NULL DEFAULT '',
    op        VARCHAR(2) NOT NULL DEFAULT '==',
    value     TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_radreply_username ON radreply(username);

CREATE TABLE IF NOT EXISTS radgroupcheck (
    id        BIGSERIAL PRIMARY KEY,
    groupname TEXT NOT NULL DEFAULT '',
    attribute TEXT NOT NULL DEFAULT '',
    op        VARCHAR(2) NOT NULL DEFAULT '==',
    value     TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_radgroupcheck_groupname ON radgroupcheck(groupname);

CREATE TABLE IF NOT EXISTS radgroupreply (
    id        BIGSERIAL PRIMARY KEY,
    groupname TEXT NOT NULL DEFAULT '',
    attribute TEXT NOT NULL DEFAULT '',
    op        VARCHAR(2) NOT NULL DEFAULT '==',
    value     TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_radgroupreply_groupname ON radgroupreply(groupname);

CREATE TABLE IF NOT EXISTS radusergroup (
    id        BIGSERIAL PRIMARY KEY,
    username  TEXT NOT NULL DEFAULT '',
    groupname TEXT NOT NULL DEFAULT '',
    priority  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_radusergroup_username  ON radusergroup(username);
CREATE INDEX IF NOT EXISTS idx_radusergroup_groupname ON radusergroup(groupname);

CREATE TABLE IF NOT EXISTS radacct (
    radacctid            BIGSERIAL PRIMARY KEY,
    acctsessionid        TEXT NOT NULL DEFAULT '',
    acctuniqueid         TEXT NOT NULL DEFAULT '',
    username             TEXT NOT NULL DEFAULT '',
    groupname            TEXT NOT NULL DEFAULT '',
    realm                TEXT NOT NULL DEFAULT '',
    nasipaddress         TEXT NOT NULL DEFAULT '',
    nasportid            TEXT NOT NULL DEFAULT '',
    nasporttype          TEXT NOT NULL DEFAULT '',
    acctstarttime        TIMESTAMPTZ,
    acctstoptime         TIMESTAMPTZ,
    acctsessiontime      BIGINT,
    acctauthentic        TEXT NOT NULL DEFAULT '',
    connectinfo_start    TEXT NOT NULL DEFAULT '',
    connectinfo_stop     TEXT NOT NULL DEFAULT '',
    acctinputoctets      BIGINT,
    acctoutputoctets     BIGINT,
    calledstationid      TEXT NOT NULL DEFAULT '',
    callingstationid     TEXT NOT NULL DEFAULT '',
    acctterminatecause   TEXT NOT NULL DEFAULT '',
    servicetype          TEXT NOT NULL DEFAULT '',
    framedprotocol       TEXT NOT NULL DEFAULT '',
    framedipaddress      TEXT NOT NULL DEFAULT '',
    acctstartdelay       INTEGER,
    acctstopdelay        INTEGER,
    xascendentsessionid  TEXT NOT NULL DEFAULT '',
    acctinputpackets     BIGINT,
    acctoutputpackets    BIGINT
);
CREATE INDEX IF NOT EXISTS idx_radacct_username    ON radacct(username);
CREATE INDEX IF NOT EXISTS idx_radacct_acctstartid ON radacct(acctstarttime);
CREATE INDEX IF NOT EXISTS idx_radacct_sessionid   ON radacct(acctsessionid);
CREATE INDEX IF NOT EXISTS idx_radacct_uniqueid    ON radacct(acctuniqueid);

CREATE TABLE IF NOT EXISTS radpostauth (
    id        BIGSERIAL PRIMARY KEY,
    username  TEXT NOT NULL DEFAULT '',
    pass      TEXT NOT NULL DEFAULT '',
    reply     TEXT NOT NULL DEFAULT '',
    authdate  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_radpostauth_username ON radpostauth(username);

-- ----------------------------------------------------------------------------
-- Business: device inventory (track every device seen on the network)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS devices (
    id          BIGSERIAL PRIMARY KEY,
    mac_address TEXT        NOT NULL UNIQUE,
    ip_address  TEXT,
    hostname    TEXT,
    vendor      TEXT,
    type        TEXT DEFAULT 'unknown',      -- phone | computer | router | ap | unknown
    source_ap   TEXT,
    online      BOOLEAN     NOT NULL DEFAULT FALSE,
    first_seen  TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_devices_mac    ON devices(mac_address);
CREATE INDEX IF NOT EXISTS idx_devices_online ON devices(online);

-- Every discovery entry (append-only) so you can see the device history.
CREATE TABLE IF NOT EXISTS device_sightings (
    id         BIGSERIAL PRIMARY KEY,
    device_id  BIGINT      NOT NULL REFERENCES devices(id),
    ip_address TEXT,
    source_ap  TEXT,
    online     BOOLEAN     NOT NULL DEFAULT TRUE,
    seen_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sightings_device     ON device_sightings(device_id);
CREATE INDEX IF NOT EXISTS idx_sightings_seen_at    ON device_sightings(seen_at);

-- ----------------------------------------------------------------------------
-- Network topology (admin map — single JSON document, exported to cet_topology.json)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS topology_document (
    id          INTEGER     PRIMARY KEY,
    data        TEXT        NOT NULL DEFAULT '{}',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- Seed default plans
-- ----------------------------------------------------------------------------
INSERT INTO plans (name, duration_seconds, price_kobo, price_currency)
VALUES
    ('15h',    54000, 20000, 'NGN'),   -- adjust price in kobo (NGN x100)
    ('Weekly', 604800, 70000, 'NGN'),
    ('Monthly', 2592000, 300000, 'NGN')
ON CONFLICT (name) DO NOTHING;

COMMIT;
