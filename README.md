# Zyranet

Vendor-agnostic paid Wi-Fi access control for the **CET-CreativeZone** network.
Standalone project (no EduAdmin integration).

The design is documented in [`docs/Zyranet-Architecture.md`](docs/Zyranet-Architecture.md).

## What it does

- Sells Wi-Fi vouchers (15-hour / weekly / monthly) via a Telegram bot.
- Accepts payment through **Flutterwave** and **Paystack** (per-user unique accounts).
- Delivers each voucher via Telegram (primary, free) with an SMS fallback (Termii).
- Enforces access with a **FreeRADIUS + CoovaChilli + PostgreSQL** stack: each voucher code is
  one-time, single-user, and expires.
- Works with old (2015) airOS / TP-Link gear — those act as transparent radios/bridges only;
  access control lives on the server.

## Layout

```
app/        Community + guest portal APIs (cradle, payments, admin) — FastAPI
bot/        Telegram bot (aiogram)
db/         PostgreSQL schema (business tables + FreeRADIUS operational tables)
raddb/      FreeRADIUS config templates (clients, sql, sites)
chilli/     CoovaChilli config template
deploy/     systemd units, nginx, backup script
docs/       Architecture document
```

## Quick start — full stack in Docker (recommended)

Everything runs in Docker with one command (Postgres + API + Telegram bot +
**FreeRADIUS**). The DB schema auto-loads on first start.

```bash
copy .env.example .env            # first time: fill in real values
docker compose up -d --build
```

- **Admin dashboard:** http://localhost:8000/admin  (login with `ADMIN_USER`/`ADMIN_PASSWORD` from `.env`)
  Dashboard has 3 tabs: **Overview** (revenue/vouchers), **Devices** (network inventory), **Live sessions** (RADIUS accounting).
- **FreeRADIUS** listens on UDP **1812** (auth) / **1813** (accounting), reads the `radcheck`/`radreply` the app writes.
- **API docs:** http://localhost:8000/docs
- **Health:** http://localhost:8000/health

Stop with `docker compose down`. Secrets come from `.env` at runtime and are
never baked into the image.

### Device tracking / connected network

A background scanner sweeps `SCAN_CIDRS` every `SCAN_INTERVAL_SECONDS`, reads the
OS ARP/neighbour table, resolves vendor from the OUI, and upserts into the
`devices` + `device_sightings` tables. It also surfaces live sessions from
`radacct`. Test the scanner manually:

```
curl -X POST http://localhost:8000/api/devices/scan   # with admin bearer token
```

> **Important (real deployment):** to see the actual LAN, the API/scanner must be
> on the network. Run the stack with host networking on the LAN server
> (`network_mode: host` for `api`/`radius` + set `SCAN_CIDRS` to your real
> subnets). CoovaChilli (the guest captive portal) also needs host networking and
> a real guest-facing NIC — see `chilli/chilli.conf` and the architecture doc.

## Dev (non-Docker)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -e ".[dev]"
uvicorn app.main:app --reload
python -m bot.main
```

## Phases

See the architecture doc. Current status: repo scaffold + schema + API/bot skeletons + infra templates.
