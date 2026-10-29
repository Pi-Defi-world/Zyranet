# Zyranet — Network Access & Billing Architecture

**Status:** Design (v1)
**Owner:** Zyranet (standalone project)
**Scope:** Vendor-agnostic paid Wi-Fi access control for the CET-CreativeZone network
**Stack:** Python 3 + FastAPI, PostgreSQL, FreeRADIUS, CoovaChilli, Telegram bot
**Runtime:** Self-hosted LAN server (Ubuntu Server)

---

## 1. Context & Goals

### 1.1 What exists

- One **Starlink** dish = the only internet source.
- **2 × TP-Link routers** — **only router #1 is wired to Starlink** (confirmed). Router #2 is not a WAN peer; it is demoted to access-point/switch mode or retired to eliminate double-NAT / DHCP conflict.
- **3 × switches** — 2015-era, most likely unmanaged (no VLAN support, no management IP).
- **4 × Ubiquiti NanoStation M2** — airMAX (airOS) PtMP radios, ~2015. One configured as a **base (AP/PtMP)**, three as **remotes (Station)** bridging separate buildings. Transparent bridges.
- A handful of indoor/outdoor **access points** that people actually join.
- Gear was previously operated under **one unified system** (a single controller/settings set) and now needs a reliable, vendor-neutral control layer.

### 1.2 Goals

1. **Structure** — every device has one clear role; traffic flows in one predictable direction.
2. **One exit point** — a single router does all NAT/DHCP/firewalling; the second router is retired or demoted.
3. **Seamless roaming** — every AP broadcasts the *same* SSID + password so phones silently roam between buildings.
4. **Paid guest access** — 15-hour / weekly / monthly vouchers, each **one-time and single-user**, enforced per-user with a time limit.
5. **Isolated admin network** — staff traffic cannot be reached by guest traffic.
6. **Vendor-agnostic** — control does not depend on any single AP brand.
7. **Zero per-message cost** — voucher/OTP delivery via Telegram (free) with SMS fallback.

### 1.3 Non-goals (this phase)

- **No EduAdmin integration.** Zyranet is a standalone repository (it happens to live inside a larger EduAdmin folder, but it has its own DB, its own auth, its own deployment).
- No microservice sprawl, no cloud dependency. Everything runs on one box on the LAN.
- No hardware replacement (yet). The design must work with 2015 gear. Where old gear is genuinely incapable (e.g., 802.1X-enterprise), control is moved upstream to the server, not shoehorned into the radio.

---

## 2. Hardware Constraints — What the 2015 Gear Can and Cannot Do

This is the most important section. Design decisions below are driven by these limits.

| Capability | NanoStation M2 (airOS 5.x) | TP-Link 2015 router (Archer/TL-WR) | TP-Link 2015 switch |
|---|---|---|---|
| Radio security | WPA2-PSK (AES) ✓ | WPA2-PSK (AES) ✓ | n/a |
| **WPA2-Enterprise / 802.1X (RADIUS per-user)** | ✗ Not supported | ✗ Not supported | n/a |
| **Native captive portal / guest hotspot** | ✗ None | Guest Network (basic, no RADIUS invoice) | n/a |
| VLAN tagging (802.1Q) | ✗ | ✗ (limited) | ✗ unlikely |
| Management UI | airOS @ `https://192.168.1.20`, `ubnt/ubnt` | `http://192.168.0.1` → `tplinkwifi.net`, `admin/admin` | none |
| Bridge mode | ✓ (default) | ✓ (AP mode) | — |

**Consequence:** the old radios *cannot* authenticate individual users at the radio. There is no way to make a NanoStation M2 and a 2015 TP-Link do per-user voucher RADIUS at the radio level. 

**The escape route:** stop trying. Treat old APs and NanoStations as **pure transparent bridges / radios** (which is exactly what they are good at), and enforce *all* access control at **one central captive-portal server** that every guest's traffic is forced through. The AP's only job is to let a phone join the radio; the server decides whether the phone gets the internet.

This makes the design **vendor-agnostic by construction** — because the control point is your server, not the AP brand. Any AP (airOS, TP-Link, UniFi, whatever you buy later) works the same way.

---

## 3. Target Topology

### 3.1 Physical layout

```
                       [ STARLINK DISH ]
                              │  Ethernet (WAN)
                              ▼
                ┌────────────────────────────┐
                │  TP-Link Router #1 (ONLY)   │   <- single gateway: NAT + DHCP + firewall
                │  second router = retired    │      or demoted to AP/switch mode
                └──────────────┬─────────────┘
                               │  LAN (VLAN-Untagged / default VLAN)
                               ▼
                      ┌──────────────────┐
                      │ Switch 1 (CORE)   │   <- unmanaged is fine; just a distribution point
                      └──┬────┬────┬─────┘
                         │    │    └────────────────────────┐
                         ▼    ▼                             ▼
              ┌────────┐ ┌────────┐   ┌───────────────┐  ┌─────────────────────┐
              │Switch 2│ │Switch 3│   │ NanoStation M2│  │ ZYRANET SERVER      │
              │Bldg A  │ │Bldg B  │   │ BASE (PtMP)   │  │ FreeRADIUS + Chilli │
              └───┬────┘ └───┬────┘   └──────┬────────┘  │ + Postgres + FastAPI│
                  ▼          ▼      air link │           └─────────┬───────────┘
            [indoor APs]  [indoor APs]        ▼                     │
            (radio only)  (radio only)   ┌────────┬────────┐       │
                                         ▼        ▼        ▼       │
                                   NanoStation NanoStation NanoStation
                                   REMOTE 1     REMOTE 2   REMOTE 3
                                       │           │          │
                                      [switch]    [switch]   [switch]
                                                                 │
                                      Each remote feeds local     │
                                      APs (radio only) ---------─┼── control plane
                                                                 ▼
                                     Guest traffic is NAT'd to gateway;
                                     the ZYRANET SERVER sits inline on the
                                     guest subnet to enforce the portal.
```

### 3.2 Logical separation

Because 2015 switches are almost certainly **unmanaged** (no VLAN support), classic 802.1Q segmentation is off the table for now. We use **IP-subnet + firewall segmentation** instead, which any modern TP-Link gateway supports and needs no switch cooperation:

| Zone | Purpose | Subnet | SSID / device |
|---|---|---|---|
| **Z_Admin** | Staff, ICT, management plane | `10.10.20.0/24` | `CET-Admin` (hidden, WPA2-PSK) + server/AP web UIs |
| **Z_Guest** | Paid public access | `172.16.30.0/24` | `CET-CreativeZone` (open/PWK, portal-controlled) |

- Both zones travel the same wires (no VLAN tags). Separation is done at the **gateway firewall** (allow/deny between `10.10.20.0/24` and `172.16.30.0/24`).
- Upgrade path: when you replace switches, tag these same subnets as VLAN 20 / VLAN 30 for true isolation. The subnets already match that plan.

### 3.3 Where control is enforced

- **Gateway router (TP-Link #1):** the single internet exit. Firewall rule set. Guest subnet is only allowed to reach the internet, the Chilli portal, and DNS — never `10.10.20.0/24` or management IPs.
- **Zyranet server (CoovaChilli + FreeRADIUS):** the only thing granting guest internet access.
- **All APs / NanoStations:** radios and bridges only. No access decisions.

---

## 4. Server Platform

### 4.1 Host

- **OS:** Ubuntu Server 22.04 LTS (x86_64, >=1GB RAM, 20GB disk) — a VM or a spare mini-PC on the LAN.
- **Location:** fixed static IP in `Z_Admin`, e.g. `10.10.20.10`.
- **Two NICs required** for CoovaChilli:
  - `eth0` (management) → `10.10.20.10`, used for admin/API/RADIUS control.
  - `eth1` (guest gateway) → `172.16.30.1`, the default gateway of the guest subnet, where CoovaChilli lives.
- **Clock sync is mandatory** for RADIUS (`systemd-timesyncd` / `chrony`).

### 4.2 Components

| Component | Role | Listen |
|---|---|---|
| **PostgreSQL 16** | Single source of truth (vouchers, plans, radius data, payments) | `5432` (localhost) |
| **FreeRADIUS 3** | RADIUS auth/accounting, `rlm_sql` against Postgres | `1812/udp`, `1813/udp` |
| **CoovaChilli** | Captive portal daemon (guest VLAN 30 gateway) | `3999` (chilli), portal on `80` |
| **daloRADIUS** | Web UI for RADIUS users/sessions/accounting (**admin UI #2**) | `80` (localhost→admin) |
| **FastAPI backend** | Voucher/payment/bot APIs + **admin dashboard (UI #1)** | `8000` (localhost) |
| **Telegram bot (aiogram)** | Purchase, OTP/voucher delivery | via webhook → FastAPI `8443` |
| **systemd / cron** | Services, maintenance jobs | — |

> **CoovaChilli is the linchpin.** It is what makes this work with old gear: it sits as the guest gateway, intercepts a guest's first HTTP request, redirects them to a login page where they enter a voucher, and — only after FreeRADIUS says the voucher is valid — opens a firewall rule granting internet. Every AP, old or new, just needs to hand guests a DHCP lease that points to Chilli as the gateway.
>
> **Guest line termination (confirmed):** the server runs a single LAN NIC. Chilli services guest DHCP (`172.16.30.0/24`, `gateway = <server IP on 172.16.30.2>` alias) and forwards guest internet upstream to the gateway router. The full path is `phone → AP → switch → router → server(config)`, and Chilli is the guest's default gateway so it sees every packet. No second VLAN interface or re-wiring required.

> **Why CoovaChilli and not the AP vendors' portals:** the old APs have no portal. CoovaChilli runs on *your* server and works behind *any* AP. It is open-source, speaks WISPr to FreeRADIUS natively, and is the standard companion of FreeRADIUS for this exact scenario.

---

## 5. Data Model (PostgreSQL)

Business tables (app-owned) plus the FreeRADIUS operational tables (standard names so `rlm_sql` works out of the box, no custom SQL module needed).

```
┌────────────────────┐     ┌──────────────────────────────┐
│ plans              │     │ vouchers                     │
├────────────────────┤     ├──────────────────────────────┤
│ id            pk   │1─∞  │ id             pk            │
│ name               │     │ code           unique (*)    │
│ duration_seconds   │     │ plan_id        fk → plans    │
│ price_kobo         │     │ valid_from     timestamptz   │
│ price_currency     │     │ valid_until    timestamptz   │
│ active   bool      │     │ mac_address    (bound MAC)    │
│                    │     │ status  enum('unused','active','expired','revoked') │
└────────────────────┘     │ created_at / used_at          │
                           │ telegram_chat_id  nullable     │
      telephone            │ max_devices int (default 1)    │
      (see users)        │──────────────────────────────│
                           └──────────────┬───────────────┘
                                          │
        ┌────────────────────┐   ┌────────▼────────────────────┐
        │ transactions        │   │ redeemed_devices            │
        `────────────────────`   ├──────────────────────────────┤
        id pk                   │ id pk                        │
        voucher_id fk → voucher │ voucher_id fk → vouchers     │
        user_id    fk → users   │ mac_address                  │
        amount_kobo             │ first_seen / last_seen       │
        provider enum('flutterwave','paystack') │ (UNIQUE voucher_id+mac; │
        provider_ref unique     │  count enforces Simultaneous-│
        status enum('pending','paid','failed') │ Use)           │
        created_at / paid_at    └──────────────────────────────┘

   ┌───────────────┐      FreeRADIUS operational tables
   │ users          │      ┌─────────┐ ┌─────────┐ ┌──────────────┐
   ├───────────────┤      │ radcheck │ │ radreply │ │ radacct/     │
   │ id pk         │      ├─────────┤ ├─────────┤ │ radpostauth  │
   │ telegram_id   │      │ username │ │ username │ │              │
   │ username      │      │ attribute│ │ attribute│ │              │
   │ telegram_name │      │ op       │ │ op       │ │              │
   │ phone         │      │ value    │ │ value    │ │              │
   │ unique 1️⃣     │      └─────────┘ └─────────┘ └──────────────┘
   │ flutterwave_  │
   │  customer_id  │      Each user is a distinct account and holds
   │ paystack_     │      its own provider reference(s): `flutterwave_
   │  customer_id  │      customer_id` and `paystack_customer_id`, so
   │ created_at    │      a purchase is always attributed to the buyer.
   └───────────────┘
```

### 5.1 How a voucher maps into RADIUS

FreeRADIUS `rlm_sql` reads `radcheck` / `radreply` by default. When a voucher is **activated** (first successful login), the backend writes:

- `radcheck`: `username = <voucher-code>`, `attribute = Cleartext-Password`, `value = <voucher-code>`
- `radreply`: `username = <voucher-code>`, `attribute = Session-Timeout`, `value = <seconds-remaining>` → kicks the user after their plan duration.
- `radreply`: `username = <voucher-code>`, `attribute = Simultaneous-Use`, `value = <max_devices>` → caps devices per voucher.

Because this is the **standard** FreeRADIUS schema, it works identically for CoovaChilli, and later for any vendor that does 802.1X/RADIUS, with **zero per-vendor code**.

### 5.2 Concurrency rule

`redeemed_devices` holds one row per (`voucher_id`, `mac_address`). On each login, the portal checks:
`SELECT count(*) FROM redeemed_devices WHERE voucher_id = :id` and denies if `>= max_devices`. With `max_devices = 1`, a voucher is **single-use**: it binds to exactly one device MAC and is used once, so the printed code cannot be passed around.

### 5.3 DDL (contract)

See `db/schema.sql` (added with the app) — the above is the authoritative shape. Key invariants:
- `voucher.code` UNIQUE.
- `plan.duration_seconds` drives `valid_until` at redemption.
- All money in kobo (integer) to avoid float errors.
- `status` transitions only forward: `unused → active → expired|revoked`.

---

## 6. Authentication Flow (Voucher → Internet)

```
[Guest phone] joins "CET-CreativeZone" (WPA2-PSK — everyone can join the radio)
     │  DHCP lease: IP=172.16.30.x, gateway=172.16.30.1 (Chilli)
     ▼
[ CoovaChilli @172.16.30.1 ]  intercepts first HTTP request
     │  redirects browser → portal login page :80/login
     ▼
[ Portal page ]  user types VOUCHER CODE
     │  Chilli sends RADIUS Access-Request  (User-Name = voucher, User-Password = voucher)
     ▼
[ FreeRADIUS ] ── rlm_sql ──► [ PostgreSQL ]
     │                                 │
     │  1. find voucher by code        │
     │  2. check valid_from <= now <= valid_until
     │  3. check redeemed_devices < max_devices
     │  4. bind MAC address (first use)
     │         │
     │   Access-Accept + Session-Timeout
     ◄──────────────────────────────┘
     ▼
Chilli opens a firewall rule for this IP → guest is live.
Session ends at Session-Timeout; on re-login the same flow re-binds the
already-registered MAC so it re-auths instantly (accounting continues).
```

Notes:
- **MAC re-auth / session persistence:** once a MAC is bound to a valid voucher, Chilli can be configured to auto-skip the login for that MAC (WISPr `sessionid` + FreeRADIUS MAC-auth), so a returning user with a live session isn't re-prompted.
- **Expiry:** FreeRADIUS simply fails auth when `valid_until` passes, so the guest is dropped. No polling job needed for enforcement.
- **Accounting** (`radacct`) logs each session for billing/reporting in daloRADIUS.

### 6.1 Admin network

`CET-Admin` uses **WPA2-PSK** (shared passphrase, hidden SSID) because old gear cannot do enterprise. Staff PCs get a DNS name / static lease; guest traffic can never route to `10.10.20.0/24` thanks to the gateway firewall. This is a pragmatic, achievable isolation for 2015 hardware.

---

## 7. FreeRADIUS Configuration Reference

Located under `raddb/`. Key files:

- `raddb/mods-enabled/sql` — DSN to Postgres, `read_clients = no` (clients are the APs, not the DB), `acct_unique = no` for testing, `postauth_query` logging.
- `raddb/mods-enabled/detail` — add `Detail-Traffic` etc. only if needed.
- `raddb/clients.conf` — every AP / Chilli that will talk RADIUS:
  ```
  client chilligw {
      ipaddr = 172.16.30.1
      secret = ZYRANET_REQUIRED_LONG_RANDOM_SECRET
      shortname = chilli-gateway
      nastype = other
  }
  ```
- `raddb/sites-enabled/default` and `raddb/sites-enabled/inner-tunnel` — auth framework; the Chilli auth uses the `default` site's `authorize`/`authenticate` (WISPr), NOT `inner-tunnel` (that's for 802.1X).
- `raddb/dictionary` — ensure WISPr attributes present (CoovaChilli uses `ChilliSpot` + `WISPr` dictionaries; ship the `chillispot` dictionary).
- CoovaChilli RADIUS: `chilli.conf` → `uamallowed`, the RADIUS host/secret matching the `chilligw` client above.

> Full working configs ship with the PoC in phase 3. The doc-level requirement: Chilli and FreeRADIUS share one secret, and FreeRADIUS treats the Chilli gateway as a trusted client.

---

## 8. Per-Vendor Integration Reference (old hardware)

These are the *radio* settings only — access control is on the server. Interfaces differ by age; these are the ones your units use.

### 8.1 NanoStation M2 (airOS)

- **Access its UI:** ethernet directly, laptop static `192.168.1.10`, browse `https://192.168.1.20` (default `ubnt`/`ubnt`). If already on the fabric, find its IP via **Fing**.
- **Main tab:** confirm **Wireless Mode** — `Access Point (PtMP)` for the base, `Station (PtMP)` for remotes. The base SSID name must appear in every remote's SSID field (that's how they pair).
- **Network tab:** set **Bridge mode** (not Router) on all — otherwise you get double-NAT.
- **Radio config:** WPA2-AES + a single shared passphrase for `CET-CreativeZone`. Do **not** attempt 802.1X-enterprise (unsupported).
- **Align tab:** only for diagnosing weak base↔remote links.

### 8.2 TP-Link router (2015, single gateway)

- **UI:** `http://192.168.0.1` or `http://tplinkwifi.net` (label on underside), `admin`/`admin`.
- **WAN:** confirm it's the unit physically wired to the Starlink ethernet port.
- **LAN → DHCP:** enabled; hand out `10.10.20.x` on the admin side. Guest subnet (`172.16.30.0/24`) is handed out by CoovaChilli, so turn DHCP off there if the router also covers it.
- **Wireless:** `CET-CreativeZone` (PSK) + `CET-Admin` (PSK, hidden). Enable "Guest Network" only if the VLAN-30 line comes from the router; best case the guest line terminates on the Zyranet server.
- **Decision rule:** the router with a live WAN to Starlink is the gateway. The other router: **unplug**, or set to **Access Point mode** (its DHCP/NAT off) if you need its radio/ports.
- **Firewall:** allow `Z_Guest → WAN` and `Z_Guest → DNS` only; deny `Z_Guest → Z_Admin`.

### 8.3 Switches (2015)

- Most are **unmanaged** — no IP, no dashboard, plug-and-forward. Run **Fing** to confirm which (if any) expose a management IP.
- For any managed one, log in and label ports ("Port 3 → NanoStation Base", "Port 5 → Switch 2 uplink"). **Label the cables** — this is the single biggest de-chaos step.
- Treat access control as the router-firewall + Chilli job (Section 3.2), not a switch VLAN job, until you replace switches.

---

## 9. Telegram Bot + FastAPI Design

### 9.1 Stack

- **FastAPI** (`app/`) — REST API + webhook receiver, `asyncpg` for Postgres, Pydantic schemas, SQLAlchemy for ORM/migrations (Alembic).
- **aiogram 3** (`bot/`) — Telegram bot. Webhook mode (no polling on the LAN server; use an inbound endpoint on `8443`).

### 9.2 Purchase & delivery flow

```
[User] /start → /buy → inline buttons: 15h | Weekly | Monthly
     │                                  (from `plans` table)
     ▼
[FastAPI] upserts a `users` row for the buyer (unique account, per-user
          flutterwave_/paystack_ customer_id) → creates `vouchers` (unused)
          + `transactions` (pending) rows
     ▼
[Payment] Checkout via chosen provider — Flutterwave or Paystack
          (per-user unique account, e.g. Paystack customer_code /
          Flutterwave customer id, so chargebacks trace to the buyer)
          │  provider webhook → FastAPI /webhooks/payment/{flutterwave|paystack}
     ▼
[Confirm] mark transaction 'paid'; mark voucher 'active' with
          valid_from=now, valid_until=now+plan.duration_seconds
     │
     ▼  deliver the code
TWO channels, always:
  ▶ Telegram message (primary, free) — if telegram_chat_id present
  ▶ SMS fallback via Termii / Africa's Talking (cheap) — if user gave a phone
     │
     ▼
[User] types code into the Chilli portal → Section 6 flow grants internet.
```

- **Redemption (confirmed):** the printed **code alone** is the credential (12-char, `secrets.token_urlsafe`). It is **one-time and single-user** — binds to the first device MAC that redeems it (Simultaneous-Use = 1) and can be used only once. A "day" voucher expires **15 hours** after activation, not 24.

### 9.3 API surface (FastAPI)

| Method/Route | Purpose |
|---|---|
| `POST /vouchers` | Create a voucher (buy) |
| `POST /webhooks/payment/{flutterwave,paystack}` | Provider confirmation → activate |
| `GET/POST /admin/*` | The **FastAPI admin dashboard** (one of the two admin UIs) |
| `POST /vouchers/{code}/activate` | Bind MAC / first-login hook (optional) |
| `GET /vouchers/{code}` | Status/remaining time |
| `POST /otp/request` + `POST /otp/verify` | SMS fallback flow |
| `GET /health` | Liveness |

### 9.4 Bot↔DB↔RADIUS coupling

Voucher activation (payment webhook) is the single write that lights the row up. No direct bot→AP coupling exists — the bot only writes to Postgres; FreeRADIUS reads Postgres at auth time. This is why the system is vendor-agnostic and stateless w.r.t. radios.

---

## 10. Deployment & Ops

### 10.1 Secret handling

- `.env` (gitignored): `DB_URL`, `RADIUS_SECRET`, `TELEGRAM_BOT_TOKEN`, `FLUTTERWAVE_{PUBLIC,SECRET}_KEY`, `PAYSTACK_{PUBLIC,SECRET}_KEY`, `TERMII_API_KEY`, admin-JWT secret.
- Never commit secrets. `raddb/clients.conf` secret is written by a deploy script from `.env`.

### 10.2 Services (systemd)

`zyranet-api`, `zyranet-bot`, `freeradius`, `chilli`, `postgresql`, plus `nginx` as reverse proxy (TLS for webhooks). Each gets a unit file under `deploy/systemd/`.

### 10.3 Backups

- Postgres nightly dump (`pg_dump`) → encrypted off-box.
- `raddb/` and `chilli.conf` are in git (with secrets templated); restore is redeploy + import dump.

### 10.4 Networking audit checklist (run before wiring ends)

Run **Fing** and answer each — these were the open unknowns:

- [ ] ~~Which TP-Link router shows a live WAN to Starlink?~~ **Answered: only router #1 is wired to Starlink** (→ keep #1 as gateway; demote #2 to AP mode or unplug)
- [ ] Which switches expose a management IP in Fing? (→ managed; label ports) vs which are invisible (→ unmanaged)
- [ ] Which NanoStation M2 is in **AP (PtMP)** mode (base) and which are **Station (PtMP)** (remotes)? Confirm all remotes share the base SSID.
- [ ] Are ALL NanoStations/APs in **Bridge** mode (no Router/Double-NAT)?
- [ ] Where does the guest line terminate — on the router or on the Zyranet server NIC? (must be able to route through Chilli)
- [ ] Have you labeled every patch cable with its endpoint?

---

## 11. Phase Plan

| Phase | Deliverable | Proof |
|---|---|---|
| **1 — Docs** | This document + repo scaffold | Reviewed, signed off |
| **2 — DB + RADIUS PoC** | Postgres schema, FreeRADIUS + CoovaChilli config, one test voucher that actually grants internet through Chilli | Two demo phones (one each side of the fabric) authenticate with the same generated voucher |
| **3 — FastAPI + Bot** | Voucher purchase via inline buttons, payment webhook, Telegram + SMS delivery, activation write | A bought voucher activates and immediately works on the portal |
| **4 — Production migration** | Firewall/zones, callers across all buildings, monitoring, backup cron | Full paid day-pass goes live |

---

## 12. Open Questions

Resolved as of this revision: **#1 (single gateway confirmed — only router #1 is wired to Starlink), #3 (Flutterwave + Paystack, per-user unique accounts), #4 (daloraDIUS AND the FastAPI dashboard — both admin UIs), #5 (printed code is the sole credential — one-time, single-user, 15-hour validity).** #2 is set to a working default (server single LAN NIC, Chilli services guest DHCP + forwards to the router) — confirm during Phase 2 wiring.

Remaining open items to confirm during implementation:

1. **Guest-subnet reachability check:** when Chilli hands out `172.16.30.0/24`, confirm the gateway router is set to route/NAT the guest subnet upstream (or that guest devices can reach the router's WAN) so internet egress works. This is a `chilli.conf` / router route decision during Phase 2.
2. **SMS provider:** Termii vs Africa's Talking for the code-only fallback (cheapest per-message; not yet chosen).
3. **Admin UI scope:** for the FastAPI dashboard — read-only voucher/usage view vs also issuing/revoking vouchers and viewing RADIUS accounting. (daloRADIUS covers the RADIUS accounting slice; decide the overlap.)

---

*This document is a design contract. Implementation tracks the phase plan; divergences should be captured here.*
