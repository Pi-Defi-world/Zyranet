# Zyranet

Zyranet is being developed as a vendor-neutral campus network operations and
access-management platform for Akwa Ibom State University of Education. The
new project baseline provides free general campus internet funded through a
University service subscription. End-user payment and voucher workflows have
been removed from the application. Existing payment-era database records are
preserved pending a separate retention decision.

The current target is described in [`docs/technical_docs1.md`](docs/technical_docs1.md)
and [`docs/proposal.md`](docs/proposal.md). These are the active project
documents; they are working drafts, not verified as-built network records.

## Current software foundation

- FastAPI, PostgreSQL, Alembic migrations, and a React/TypeScript operations UI.
- A versioned `/api/v1` foundation for locations, device models, devices,
  interfaces, addresses, topology, and audit history.
- Early network discovery using bounded subnet probes and local neighbour data.
- Optional, manually initiated SNMP/LLDP discovery for compatible equipment.
- Authentication integration and FreeRADIUS remain conditional on testing the
  installed access points and gateway. No end-user payment flow is included.

## Readiness boundary

The repository is ready for controlled software and schema testing. It is not
yet ready to operate the campus network as a production NMS. The active project
manual remains the target; these are the remaining evidence gates:

| Capability | Current implementation | Evidence needed before campus production |
| --- | --- | --- |
| Inventory and topology | Normalized records, audited edits, confidence/evidence, export | ICT reconciliation against the physical site survey |
| Discovery and device inspection | Bounded subnet discovery and generic read-only SNMP identity | Approved management CIDRs and checks against representative installed models |
| Starlink A/B health | Not independently measured by the application | Confirmed gateway/device API that can test each circuit separately; a default-route internet probe cannot distinguish WAN A from WAN B |
| Alerts and incidents | Not implemented as an operator workflow | Monitoring source, thresholds, acknowledgement, resolution and outage exercise |
| Hardware configuration | No configuration writes | Device-specific adapter, backup/rollback, approval and lab/field acceptance; this is intentionally outside the current release |
| Database recovery | Encrypted backup script and PostgreSQL migration round-trip tests | Restore an encrypted archive into a clean isolated host and verify application data |
| User access and RADIUS | Single configured administrative identity; RADIUS is conditional | Approved identity lifecycle and compatibility test with the actual gateway/AP models |

These boundaries keep unknown campus hardware from being represented as
verified telemetry or controllable equipment.

## Layout

```
backend/     FastAPI app, Alembic migrations, PostgreSQL schema and tests
  app/       Operations APIs, /api/v1 inventory, security core
  alembic/   Migrations (single source of schema truth — schema.sql is the
             baseline applied idempotently by 0001_baseline)
  db/        PostgreSQL schema + native install scripts
  tests/     pytest suite (API, security, migrations)
frontend/    React + TypeScript + Vite admin dashboard (Tailwind)
raddb/       FreeRADIUS config templates (clients, sql, sites)
chilli/      CoovaChilli config template
deploy/      systemd units, nginx, backup script
docs/        Architecture + implementation docs
```

## Local development stack

The base Docker Compose file runs PostgreSQL, the API, and a separate discovery
worker. FreeRADIUS is an optional Compose profile with loopback-only clients;
it will not accept network devices until a confirmed NAS is explicitly added
after the authentication design is approved.
CoovaChilli is not included. The local API port is published on loopback only.
The host-network override is for a reviewed management host; it gives the
worker access to the host's network namespace. Schema is applied automatically
by Alembic in the development Compose stack.

```bash
copy .env.example .env            # first time: fill in real values
docker compose up -d --build
```

- **Operations dashboard:** http://localhost:8000/ (login with `ADMIN_USER`/`ADMIN_PASSWORD` from `.env`)
- **Admin alias:** http://localhost:8000/admin (redirects to the operations dashboard)
- **API docs:** http://localhost:8000/docs
- **Health:** http://localhost:8000/health

Stop with `docker compose down`. Secrets come from `.env` at runtime and are
never baked into the image.

### Production deployment boundary

`docker-compose.prod.yml` assumes a separately managed PostgreSQL service on
the host, a host-installed nginx reverse proxy, and a valid TLS certificate.
The API binds to `127.0.0.1:8000`; nginx serves the dashboard, proxies the API
and health checks, and terminates HTTPS. The API port must not be opened to the
campus LAN. The discovery worker uses host networking, so enable it only on a
trusted management host and keep discovery disabled until the management CIDRs
are approved.

Before production, create `.env` and replace every placeholder. Set
`APP_ENV=production`, use a random `ADMIN_JWT_SECRET` of at least 32 characters,
an `ADMIN_PASSWORD` of at least 12 characters, and a unique database password
of at least 20 characters. Set `ALLOWED_HOSTS` to the actual dashboard hostname
plus loopback, and `CORS_ALLOWED_ORIGINS` to that hostname's HTTPS origin. The
application refuses to start in production with placeholder secrets, wildcard
hosts, or non-HTTPS CORS origins. Keep `.env` readable only by the service
operator. Configure the host PostgreSQL database/user and certificate paths
before starting services.

The production sequence is deliberate: verify a database backup, apply schema
migrations as an explicit operator action, then start the API and worker.

```bash
docker compose -f docker-compose.prod.yml run --build --rm migrate
docker compose -f docker-compose.prod.yml up -d --build
```

Install `deploy/nginx.conf` after replacing the example hostname and TLS
certificate paths, then validate it with `nginx -t` before reloading nginx.
That sample proxies `/`, `/api/`, and actual application health endpoints;
it does not synthesize a healthy response when the application is unavailable.

`deploy/backup.sh` writes a PostgreSQL custom-format archive, checks that
`pg_restore` can read its catalogue, encrypts it to a configured GPG recipient,
and stores it with owner-only permissions before pruning old archives. Install
the recipient public key for the scheduled account and provide PostgreSQL
credentials through local peer authentication or a mode-0600 `.pgpass` file;
do not place the database password on the command line. Copy encrypted archives
to a separate recovery target. Restore one into an isolated database using the
private key and `pg_restore` as part of the production acceptance drill. The
repository does not claim that a restore drill has already passed.

### Migrations

Alembic is the sole schema initializer. To apply migrations on an existing
database (including one previously created from `db/schema.sql` — the baseline
is idempotent, no `stamp` needed), verify a backup first and apply migrations
explicitly for production:

```bash
cd backend
alembic upgrade head
```

Revision `0006_normalized_topology` preserves the legacy JSON topology rows.
Its downgrade removes the new normalized topology tables and their records, so
export or back them up before reversing that revision. The CI migration test
uses a disposable PostgreSQL database to test schema upgrade, model drift, and
downgrade/re-upgrade; never point it at an operational database.

### Device tracking / connected network

A separate worker sweeps the explicitly configured `SCAN_CIDRS` every
`SCAN_INTERVAL_SECONDS`, reads the host OS neighbour table, resolves vendor
from the OUI, and upserts observations into `devices` and `device_sightings`.
Discovery is disabled by default. Set `SCAN_ENABLED=true` only after entering
approved, verified management CIDRs in `SCAN_CIDRS`.
Each sweep is recorded in `discovery_runs`; observations retain the run, source,
and probe evidence. Stable-device sightings are sampled at
`SCAN_SIGHTING_INTERVAL_SECONDS` to keep the history bounded.
Each configured subnet and the whole sweep are capped by
`SCAN_MAX_HOSTS_PER_SUBNET` and `SCAN_MAX_HOSTS_TOTAL`. This is early
visibility, not authoritative Wi-Fi association or complete campus discovery.
Oversized subnets are skipped in full; split only approved scan ranges into
smaller CIDRs instead of relying on a partial sweep.
Authenticated read endpoints are available at `/api/v1/discovery/runs` and
`/api/v1/discovery/runs/{run_id}/observations`; operators can review these in
the authenticated `/discovery` dashboard. Runs are marked partial when scope
entries are invalid, unsupported, capped, or probe execution reports errors.
After a worker restart, abandoned runs are closed as failed once they exceed the
configured recovery window.
Operators can request a sweep with `POST /api/v1/discovery/runs`; this persists
a queued run and returns immediately. The dedicated worker claims it, and the
database prevents multiple queued/running sweeps at once. A request is rejected
with `409` while a scan is already queued or running.

### Read-only hardware inspection

`GET /api/v1/adapters` lists implemented protocol capabilities. The first
adapter is generic SNMPv2c and reads only standard `sysName`, `sysDescr`,
`sysObjectID`, and `sysUpTime` fields. Operators can request one inspection with
`POST /api/v1/devices/{id}/inspect`; the device's current IP must exactly match
an entry in `SNMP_TARGETS`. Results are audited and returned as evidence; they
do not overwrite the inventory model or claim vendor-specific support. Device
configuration writes are not implemented.
SNMP communities have no built-in `public` fallback. Store the configured
community in protected runtime configuration and allow SNMP only across the
management network; SNMPv2c does not encrypt credentials or payloads.

PySNMP is constrained to `>=7.1,<8`: the former synchronous high-level API was
removed in PySNMP 6.2, while Zyranet's discovery and identity adapters use the
maintained asyncio API.

The topology dashboard reads the normalized `devices`, `links`, and
`link_endpoints` records. The graph does not use the legacy JSON planning map or
infer physical paths from scan sightings. Operators can record A/B link
endpoints against device and optional interface IDs; moving a link to `verified`
requires a confidence value and written evidence. Append-only evidence is
stored in `topology_observations` and each topology write is audited. Existing
JSON topology documents remain preserved for review, but the new graph ignores
them until their claims are reconciled with the field audit.

The related API resources are `GET/POST /api/v1/links`,
`PATCH /api/v1/links/{id}`, `GET/POST /api/v1/topology-observations`, and
`GET /api/v1/topology/physical-graph`. JSON and CSV snapshots are available at
`GET /api/v1/topology/export?format=json|csv`; they include link endpoints and
append-only topology evidence. Device deletion is blocked while normalized
links or topology evidence reference it; retire the device instead. The current
docs report two Starlink services, but they are not drawn as connected hardware
until they have inventory and verified interface/link records.
> **Important:** discovery only sees networks reachable from the worker's
> network namespace and its neighbour table. The host-network override gives it
> LAN visibility but also grants broad host-network access; use it only on a
> trusted management host with approved CIDRs. Device configuration writes are
> not implemented.

## Dev (non-Docker)

Backend (Python ≥ 3.11):

```bash
cd backend
pip install -r requirements.lock
pip install pytest pytest-asyncio ruff httpx       # dev and API test tools
alembic upgrade head                               # needs DB_URL or DB_* vars
uvicorn app.main:app --reload                      # http://localhost:8000
python -m app.worker

python -m ruff check .        # lint
python -m pytest -q           # tests (set TEST_MIGRATION_DATABASE_URL for PG migration tests)
```

Frontend (Node ≥ 20.19):

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to :8000

npm run lint       # oxlint
npm run typecheck  # tsc
npm run test       # vitest
npm run build      # production build
```

## Security (R0)

- Login uses Argon2 hash comparison (`check_login`) with constant-time semantics.
- Failed logins are throttled per (client IP, username) — `LOGIN_MAX_ATTEMPTS` /
  `LOGIN_LOCKOUT_SECONDS` — and audited.
- JWTs carry `role`/`iss`/`aud`; endpoints under `/api/v1` enforce
  `viewer` (read) / `operator` (write) / `admin` roles via `require_role`.
- TrustedHost + restrictive CORS (`CORS_ALLOWED_ORIGINS`) + request-ID access
  logs (`LOG_FORMAT=json|text|auto`).
- Release-1 rule: **read-only toward network devices** — no config writes.

## CI

`.github/workflows/ci.yml` runs on every push/PR:

- **deployment-config** — validates all Compose modes and builds the production container image
- **backend** — ruff + pytest
- **migrations** — Alembic upgrade, model-drift check, and downgrade/re-upgrade against PostgreSQL 16
- **frontend** — oxlint + tsc + vitest + production build

## Phases

Current implementation: security foundation, Alembic migrations, inventory,
topology, audit history, bounded discovery, read-only hardware inspection, and
the React operations dashboard. End-user payment and voucher runtime paths
have been removed. Legacy payment data in an existing database is retained;
fresh database initialization no longer creates those legacy tables. See the
implementation plan in `docs/technical_docs1.md` for the remaining phases.
