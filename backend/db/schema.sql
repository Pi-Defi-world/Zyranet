-- ============================================================================
-- Zyranet PostgreSQL schema for network operations and optional FreeRADIUS.
-- Legacy payment tables are not created for new installations. Existing
-- deployments retain those tables until their data retention is reviewed.
-- ============================================================================

BEGIN;

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

COMMIT;
