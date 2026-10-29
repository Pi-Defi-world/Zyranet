# Zyranet redesign plan — campus connectivity for 300+ users

The discovery answers point to a clear strategy: build a low-cost, centrally managed campus network that can grow without requiring you to replace all the old equipment.

The design must support 3–5 buildings, a converted workspace, 300+ concurrent users, one Starlink connection initially, and a possible second connection later. Because the equipment models are not yet known, we should avoid buying a complete new network before testing what you already own.

I recommend treating this as two connected projects:

1. The physical campus network: get reliable internet from Starlink to every building, with appropriate capacity, isolation, and failover options.
2. The Zyranet software platform: manage identities, network access, devices, monitoring, policies, and reports through one professional interface.

The network must remain usable if the Zyranet dashboard is temporarily unavailable. Authentication and enforcement should be designed so a web-interface outage does not automatically take down every connected user.

## 1. Repository audit: what we can reuse

I inspected the current `main` branch's README, Docker Compose configuration, database schema, FastAPI entrypoint, authentication routes, device APIs, network-topology APIs, settings, and admin HTML.

The good news is that Zyranet already has a foundation for the new product. We should evolve it instead of throwing everything away.

Keep and extend

- FastAPI application and PostgreSQL persistence.
- Device inventory and discovery history.
- Network topology editor and SNMP discovery scaffolding.
- Live RADIUS session reporting.
- Admin authentication foundation and dashboard shell.
- Docker-based development and deployment approach.

Refactor substantially

- Voucher-oriented users and access policies.
- Revenue-centric dashboard and navigation.
- Topology and device data model.
- Authentication, permissions, monitoring, and network integrations.
- Configuration management and deployment assumptions.

Remove from the core product

- Flutterwave and Paystack checkout.
- Transaction and pricing-plan workflows.
- Payment-specific voucher activation.
- Termii/SMS purchase delivery and payment-specific configuration.
- Telegram purchase flows, unless a separate operational notification use case justifies keeping the bot.

### Specific repository changes

These are grounded in the files I inspected:

| Existing file/module                          | Proposed change                                                                                                          |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `app/main.py`                                 | Keep the application entrypoint; separate monitoring workers from API startup and tighten CORS configuration.            |
| `app/routers/payments.py`                     | Remove from the core API after identifying and migrating all dependencies.                                               |
| `app/routers/vouchers.py`                     | Replace purchase/activation workflows with access-policy and temporary guest-access workflows.                           |
| `app/routers/auth.py`                         | Expand beyond the current login endpoint into user lifecycle, sessions, roles, and secure administration.                |
| `app/routers/devices.py`                      | Keep inventory and discovery; add building/location assignment, health state, and manageable-device capabilities.        |
| `app/routers/network.py`                      | Keep the topology editor; make physical links, VLANs, device relationships, and discovery confidence explicit.           |
| `app/services/scanner.py`                     | Keep basic LAN discovery, but distinguish a device being observed on a subnet from knowing its actual Wi-Fi association. |
| `db/schema.sql`                               | Introduce a versioned migration strategy and new school, identity, policy, location, and monitoring models.              |
| `app/static/admin.html` and `app/static/css/` | Redesign the interface around network operations rather than vouchers and revenue.                                       |
| `docker-compose.yml`                          | Reconcile the deployment with the actual network services and document a production-safe topology.                       |

Source files: [application entrypoint](https://github.com/Pi-Defi-world/Zyranet/blob/main/app/main.py?utm_source=chatgpt.com), [database schema](https://github.com/Pi-Defi-world/Zyranet/blob/main/db/schema.sql?utm_source=chatgpt.com), [network API](https://github.com/Pi-Defi-world/Zyranet/blob/main/app/routers/network.py?utm_source=chatgpt.com), [device API](https://github.com/Pi-Defi-world/Zyranet/blob/main/app/routers/devices.py?utm_source=chatgpt.com).

### Four important findings to resolve early

1. The current deployment files disagree with the documented deployment. The README describes PostgreSQL, API, Telegram bot, and FreeRADIUS in the Docker stack, but the inspected `docker-compose.yml` defines only PostgreSQL, API, and bot. We need to establish how RADIUS and CoovaChilli are actually deployed before designing migration steps.
2. Authentication is still administrator-centric. The inspected auth router exposes a username/password login that returns a token. That is not yet a complete school identity system with student accounts, staff roles, provisioning, and account lifecycle management.
3. The database is tightly coupled to payments. The current schema contains payment providers, transaction records, purchase plans, and vouchers. We need a migration that preserves useful device history and administrative records while removing the old business model safely.
4. Network discovery has limits. The current scanner reads local ARP/neighbour information and records sightings. This can identify some devices, but it cannot reliably reveal all clients, their associated access point, signal quality, or actual throughput across every building. Those capabilities require compatible network hardware, controller telemetry, SNMP, or other supported integrations.

One additional issue: the inspected FastAPI entrypoint allows all CORS origins. Before exposing the new dashboard beyond a trusted development environment, we should restrict browser origins, secure the token lifecycle, enforce authorization on every management action, and verify that secrets and management interfaces are not exposed to guest networks.

Migration rule: do not simply delete the old tables or overwrite the existing database. Back up the database, introduce versioned migrations, preserve useful inventory and topology data, and retire payment-related records according to the school's retention requirements.

## 2. Recommended physical network topology

For 300+ concurrent users across several buildings, we should separate the internet gateway, campus distribution, management services, and user networks.

Starlink — primary WAN

Possible second WAN in a later phase

VLAN-capable main gateway

Firewall, DHCP, routing, DNS policy, QoS, WAN failover

Core managed switch

Building uplinks, network segmentation, PoE where supported

ICT services

Zyranet, database, monitoring, RADIUS

Management network

Switch, router, radio and AP administration

Wired building uplinks

Ethernet or fiber to remote distribution switches

Wireless building bridges

Existing outdoor transmitters and receivers where needed

Access layer — each building

Local switches → indoor access points → student, staff and guest devices

The diagram represents the target logical design, not a claim that your existing devices support all of it.

### Network separation

I recommend planning the following logical networks. The exact IP ranges should be selected after inventorying the existing LANs to avoid address conflicts.

| Network        | Purpose                                     | Access rule                                     |
| -------------- | ------------------------------------------- | ----------------------------------------------- |
| Management     | Router, switch, radio and AP administration | ICT administrators only                         |
| Servers        | Zyranet, database, RADIUS and monitoring    | Explicitly permitted services                   |
| Staff          | Staff and administrative devices            | School-approved resources                       |
| Students       | Student devices                             | Internet and permitted learning resources       |
| Labs/workspace | Shared computers and workspace devices      | Policy-based access                             |
| Guest          | Visitors and temporary users                | Internet only, client isolation where supported |

Use VLANs on managed switches and the gateway wherever possible. Existing unmanaged switches can be retained for carefully chosen edge segments, but they must not be treated as security boundaries.

If the old equipment cannot support the required isolation, the correct response is to change where that segment connects or replace the particular device—not to assume the dashboard can compensate for a missing network control.

## 3. Hardware reuse and minimum procurement plan

With a minimal budget, our objective is not to buy a new network. It is to identify the smallest number of upgrades needed to make the existing network reliable and secure.

### Equipment inventory

Before purchasing anything, record each device's model, hardware revision, firmware, power supply, port speeds, PoE requirements, operating condition, and current role.

| Existing equipment                 | Reuse strategy                                                                          | Replace only if…                                                                        |
| ---------------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Starlink                           | Keep as the initial WAN                                                                 | Its performance, placement, or service limitations prevent the required operation       |
| Main router                        | Keep if it supports the required routing, firewall rules, VLANs, and bandwidth controls | It cannot enforce the network policies we need                                          |
| Indoor access points               | Retain working units for coverage and low-density areas                                 | They cannot support adequate capacity, security, or reliable operation                  |
| Outdoor transmitters and receivers | Reuse as building bridges if compatible and stable                                      | The link is unreliable, lacks adequate throughput, or cannot meet security requirements |
| Unmanaged switches                 | Retain for appropriate edge connections                                                 | VLAN separation, monitoring, or uplink capacity is needed at that point                 |
| LAN cables                         | Test, label, and reuse serviceable runs                                                 | They fail testing, are damaged, or are unsuitable for the run                           |
| Existing server or spare computer  | Host Zyranet and network services initially                                             | It cannot provide stable operation, storage, or sufficient resources                    |

### What I would prioritize buying

Priority 1 — A capable main gateway, if your current router fails the audit

It must support VLANs, firewall policies, DHCP, routing, bandwidth management, and preferably multi-WAN failover. Do not buy a second Starlink or an expensive router before confirming this gap.

Priority 2 — Managed switches at strategic distribution points

Start with the core and any building connection that requires VLAN separation. Verify port counts, uplink speed, and PoE needs before choosing models.

Priority 3 — Additional access points only where measurements show a gap

A target of 300+ concurrent users does not automatically mean a particular number of APs. Client mix, airtime utilization, interference, room layout, and radio capacity determine the real requirement.

Priority 4 — Cable testing, power protection, and link repairs

A cable tester, proper termination tools, labeled patch cables, and appropriate surge protection may deliver more value than replacing equipment that still works.

I would not set a hardware budget in naira yet. We don't know the models, how many access points work, which cables reach each building, or whether the main router can support VLANs. Giving a fixed shopping list now risks spending money on equipment you already have or buying components that are incompatible.

### How to handle 300+ concurrent users

Treat 300 as a capacity target to validate, not just a client count to display.

- Measure the actual Starlink download and upload speeds during busy periods.
- Estimate simultaneous video calls, classroom streaming, downloads, browsing, and administrative traffic.
- Survey each building for coverage, interference, and usable throughput.
- Test the busiest areas under realistic load.
- Prioritize interactive educational traffic over bulk downloads where appropriate.
- Record where the bottleneck occurs: WAN, radio backhaul, access point, switch uplink, or server.

A well-placed AP with a clean wired backhaul can outperform several poorly placed APs sharing a congested wireless uplink.

For building-to-building links, prefer existing wired runs when they are suitable. Where wireless bridges are necessary, use dedicated backhaul radios where available rather than forcing all building traffic through a congested client-facing radio.

## 4. Authentication: the school-friendly model

Since you have not chosen an identity provider, I recommend a staged approach that supports individual accountability without making initial deployment too expensive.

## Recommended identity strategy

School-managed identity

Maintain users, roles, status, groups, and access eligibility in Zyranet initially. Support imports from existing student/staff records using a controlled CSV process, with an API integration added later if needed.

Staff and privileged accounts

Use individual accounts, strong passwords, and multifactor authentication for administrators. Use enterprise Wi-Fi authentication on compatible equipment; do not rely on a shared staff password as the long-term design.

Student-owned devices

Start with a secure captive portal using individual school credentials if the gateway supports it reliably. Add enterprise Wi-Fi authentication and supported device onboarding as the network is upgraded.

Guest access

Staff-approved temporary accounts or access codes with expiry, usage limits, and internet-only permissions. No payment process is required.

### Important authentication details

- RADIUS remains a candidate, not a commitment. Keep FreeRADIUS if it fits the selected gateway and access-point ecosystem.
- CoovaChilli is conditional. Retain it only if the chosen captive-portal design and network topology justify it. It should not be placed into the architecture simply because the old project used it.
- Use WPA2/WPA3-Enterprise where supported for individual network credentials. Legacy access points may need to be replaced in selected locations.
- MAC address registration can be useful for inventory and device policies, but randomized MAC addresses make it unsuitable as the sole identity or security mechanism.
- Keep student, staff, guest, and management traffic isolated at the network layer. A user being authenticated must not automatically give them access to every internal resource.
- Use an explicit account lifecycle: pending → active → suspended/expired. Disabling an account should revoke future authentication and terminate active sessions where the network supports it.

### Proposed identity data model

Rather than making Telegram the primary identity, introduce school-centric entities:

- `users` — account identity, status, and timestamps.
- `roles` and `user_roles` — administrator, ICT operator, staff, student, and guest permissions.
- `groups` — classes, departments, staff teams, and other school groups.
- `devices` and `user_devices` — inventory and optional user/device associations.
- `access_policies` — network, group, schedule, quota, and session rules.
- `auth_events` and `sessions` — authentication outcomes, active sessions, and revocation records.
- `locations` — campus, building, floor, room, and network zone.

Keep these concepts separate from the network equipment's own credentials. A Zyranet administrator login should not automatically grant unrestricted SSH, SNMP, or router-configuration access.

## 5. Redesigned Zyranet software architecture

I'd keep a modular monolith for the first release. It is easier to deploy and maintain on a limited budget, while still allowing the project to add separate workers when monitoring load justifies them.

\#chatgpt-mermaid-\_r_km\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_km\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_km\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_km\_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_km\_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_km\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_km\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_km\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_km\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_km\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_km\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_km\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_km\_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_km\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-\_r_km\_ p{margin:0;}#chatgpt-mermaid-\_r_km\_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_km\_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_km\_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_km\_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-\_r_km\_ .label text,#chatgpt-mermaid-\_r_km\_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_km\_ .node rect,#chatgpt-mermaid-\_r_km\_ .node circle,#chatgpt-mermaid-\_r_km\_ .node ellipse,#chatgpt-mermaid-\_r_km\_ .node polygon,#chatgpt-mermaid-\_r_km\_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_km\_ .rough-node .label text,#chatgpt-mermaid-\_r_km\_ .node .label text,#chatgpt-mermaid-\_r_km\_ .image-shape .label,#chatgpt-mermaid-\_r_km\_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-\_r_km\_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-\_r_km\_ .rough-node .label,#chatgpt-mermaid-\_r_km\_ .node .label,#chatgpt-mermaid-\_r_km\_ .image-shape .label,#chatgpt-mermaid-\_r_km\_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-\_r_km\_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-\_r_km\_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_km\_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_km\_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-\_r_km\_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-\_r_km\_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_km\_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_km\_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_km\_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-\_r_km\_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-\_r_km\_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_km\_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_km\_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-\_r_km\_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_km\_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-\_r_km\_ .icon-shape,#chatgpt-mermaid-\_r_km\_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_km\_ .icon-shape p,#chatgpt-mermaid-\_r_km\_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-\_r_km\_ .icon-shape .label rect,#chatgpt-mermaid-\_r_km\_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_km\_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-\_r_km\_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-\_r_km\_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_km\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_km\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_km\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_km\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_km\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_km\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_km\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_km\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_km\_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-\_r_km\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_km\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_km\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_km\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_km\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_km\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_km\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_km\_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_km\_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_km\_ .node tspan[font-weight="normal"],#chatgpt-mermaid-\_r_km\_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-\_r_km\_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-\_r_km\_ .node rect,#chatgpt-mermaid-\_r_km\_ .node circle,#chatgpt-mermaid-\_r_km\_ .node ellipse,#chatgpt-mermaid-\_r_km\_ .node polygon,#chatgpt-mermaid-\_r_km\_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_km\_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-\_r_km\_ .mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2,2;}#chatgpt-mermaid-\_r_km\_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-\_r_km\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_km\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}Zyranet Web DashboardStudent and Guest PortalFastAPI ApplicationIdentity and Policy ModuleInventory and TopologyModuleMonitoring and AlertsNetwork Device AdaptersPostgreSQLFreeRADIUSGateway, Switches, Radios, APs

The key boundary is between desired configuration and observed network state. An administrator might configure a policy, but Zyranet should show whether that policy was actually applied, rejected, or could not be verified.

### Proposed repository structure

This is the target structure, not a claim that these modules already exist.

```
Zyranet/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── security.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── policies.py
│   │   ├── devices.py
│   │   ├── network.py
│   │   ├── monitoring.py
│   │   └── reports.py
│   ├── services/
│   │   ├── identity/
│   │   ├── access_control/
│   │   ├── inventory/
│   │   ├── topology/
│   │   ├── monitoring/
│   │   └── adapters/
│   ├── models/
│   ├── schemas/
│   └── static/
├── db/
│   ├── migrations/
│   └── schema.sql
├── raddb/
├── chilli/
├── deploy/
├── tests/
├── docs/
│   ├── architecture/
│   ├── network-design/
│   ├── operations/
│   └── security/
├── docker-compose.yml
└── pyproject.toml
```

The existing `app/routers/` and `app/services/` layout already gives us a starting point. I would not reorganize every file in one giant refactor. Introduce the new modules incrementally and migrate each existing route with tests.

### Database migration plan

Keep the existing `devices`, `device_sightings`, and `topology_document` data where it is useful. Introduce versioned migrations for the new entities, then move the application away from payment-specific tables.

Do not use the current `schema.sql` as a fresh production database initialization strategy indefinitely. It seeds purchase plans and uses `CREATE TABLE IF NOT EXISTS`, which is not a substitute for controlled upgrades to an existing database.

For the first release, I would add:

- Campus locations and hierarchical building records.
- Network devices and their supported capabilities.
- Physical and logical links.
- User identities, groups, roles, and lifecycle status.
- Access policies and policy assignments.
- Authentication events and session records.
- Monitoring measurements, alerts, and audit logs.
- Configuration changes, deployment status, and failure records.

### Monitoring: what the dashboard can really show

We should support different telemetry levels instead of inventing metrics.

| Data source                   | What Zyranet can reasonably report                                                      |
| ----------------------------- | --------------------------------------------------------------------------------------- |
| Local ARP/neighbour discovery | Devices recently observed on a reachable subnet                                         |
| FreeRADIUS accounting         | Authenticated sessions and reported session usage                                       |
| SNMP on supported devices     | Interface counters, status, and device metrics exposed by the equipment                 |
| Supported controller/API      | Client association, radio health, signal metrics, and AP-specific details where exposed |
| Active probes                 | Connectivity, latency, packet loss, and DNS reachability                                |
| Gateway metrics               | WAN throughput and connection health, subject to device support                         |

The interface should label stale, unavailable, and estimated values explicitly. For example, an access point last seen ten minutes ago is not necessarily offline; it may simply be unmonitored or unreachable from the management subnet.

## 6. The user interface and operating experience

The admin portal should be built around daily tasks the school's ICT team actually performs.

## Proposed dashboard home

Internet

# Healthy / Degraded

Based on live probes

Connected clients

# Live count

From available telemetry

Network devices

# Healthy / Alerting

By location

Open incidents

# Prioritized list

With acknowledgment and history

Primary navigation

Network map

Buildings

Users and groups

Access policies

Monitoring

Reports and audit

Conceptual layout only; these are not live metrics from the existing network.

For the visual design, I would retain the current network-map functionality, but make it one section of the application rather than the whole experience. The new interface should be responsive, accessible, fast on ordinary school computers, and usable over the local network even when the external internet is degraded.

For students, use a separate, minimal connection experience: a school-branded sign-in page, clear connection status, and a way to get help. Do not expose network inventory, administrative actions, or other users' information through the student portal.

## 7. Phased implementation roadmap

The roadmap below prioritizes restoring a reliable campus network before building advanced management features. Time estimates are planning ranges, assuming one primary developer and limited hardware budget; they will change after the repository and network inventory are fully validated.

## 1

Phase 1 — Audit and network discovery

1–2 weeks

Foundation

- Inventory all routers, APs, outdoor radios, switches, and cable runs.
- Document building layouts, cable paths, link speeds, and existing IP ranges.
- Back up the existing database and configurations.
- Test Starlink performance at different times.
- Verify which software services currently work and how RADIUS is deployed.

Exit condition: a verified inventory, current-state topology, and a list of critical gaps.

## 2

Phase 2 — Stable network foundation

2–4 weeks

- Stabilize the main gateway and building backhaul.
- Configure the required network separation.
- Establish a management subnet and secure device administration.
- Test coverage and capacity in the workspace first.
- Document rollback and recovery procedures.

Exit condition: stable internet and verified isolation in the initial workspace.

## 3

Phase 3 — Zyranet core redesign

2–4 weeks

- Introduce database migrations and new identity models.
- Remove payment dependencies from the core application.
- Implement user roles, access policies, device inventory, and audit events.
- Restrict CORS and harden authentication.
- Add automated tests for policy enforcement and authorization.

Exit condition: a tested, payment-independent Zyranet core.

## 4

Phase 4 — Authentication and operations UI

2–4 weeks

- Build school account provisioning and role management.
- Integrate the chosen RADIUS/captive-portal strategy.
- Implement the redesigned dashboard and network map.
- Add monitoring, alerts, reports, and session management.
- Test student, staff, guest, and administrator workflows.

Exit condition: the ICT team can manage real users and monitor the network through Zyranet.

## 5

Phase 5 — Campus expansion and hardening

2–4 weeks

- Extend service to the remaining buildings.
- Test 300+ concurrent clients through realistic load tests.
- Validate failure recovery, backup restoration, and access revocation.
- Produce school-facing documentation and reports.
- Evaluate whether a second Starlink or additional APs are justified.

Exit condition: measured campus coverage, documented operating procedures, and a defensible production-readiness decision.

These phases overlap where practical. The indicative total is roughly 9–18 weeks, but the physical network and existing code may introduce additional work. We should not declare production readiness based on the calendar alone.

## 8. Security and operational requirements

For a school, security is not an optional upgrade.

The minimum production requirements should include:

- Administrative MFA, least-privilege roles, secure password storage, token expiry, and revocation.
- Firewall rules that block guest and student access to management interfaces and unauthorized internal resources.
- Restricted API and browser access, input validation, rate limiting, and audit logs for sensitive actions.
- HTTPS for the web dashboard and captive portal wherever credentials are submitted.
- Secrets supplied at runtime rather than embedded in source code or container images.
- Automated database backups, an off-device backup copy, and a tested restoration procedure.
- Monitoring of the gateway, critical uplinks, APs, server health, disk usage, and authentication failures.
- A documented emergency procedure for restoring internet access if Zyranet is unavailable.
- Appropriate retention and access controls for student identities and connection logs.

For resilience, authentication and monitoring must be tested separately. A monitoring outage should not disable internet access. If the authentication server fails, the network should follow an explicitly chosen policy rather than silently granting unrestricted access.

## 9. Make it presentable to the school

I would not pitch this as merely a Wi-Fi upgrade. Present it as a managed digital infrastructure project with a measurable outcome.

PROPOSED SCHOOL PROJECT

# Zyranet Campus Connectivity

Reliable internet. Controlled access. Centralized visibility.

A campus-wide connectivity and network operations platform designed to connect school buildings through existing wired and wireless infrastructure, provide appropriate access to students and staff, and give the ICT department a single place to manage and monitor the network.

What the school receives

- Extended internet coverage across 3–5 locations.
- School-managed access policies and individual authentication.
- Centralized network monitoring and device inventory.
- Better control over bandwidth and access to internal resources.
- Operational reports, incident history, and recovery documentation.
- A phased upgrade plan that prioritizes reuse of existing equipment.

The school should receive a short implementation proposal containing the current-state network map, target architecture, hardware inventory, risks, phased budget, success criteria, and operating responsibilities. Avoid promising seamless roaming, full device visibility, or 300-user capacity until those capabilities have been tested on the actual hardware.

## 10. What counts as success?

Before going live, agree on measurable acceptance criteria.

| Area           | Acceptance test                                                                                       |
| -------------- | ----------------------------------------------------------------------------------------------------- |
| Coverage       | Required workspaces and buildings pass documented connectivity tests                                  |
| Capacity       | Load tests demonstrate acceptable performance with a representative 300+ client workload              |
| Authentication | Each user category can authenticate, and disabled accounts lose access as intended                    |
| Isolation      | Student and guest devices cannot reach protected management interfaces                                |
| Monitoring     | The dashboard accurately reflects the telemetry available from each device                            |
| Recovery       | Database restoration and network recovery procedures are tested                                       |
| Administration | Authorized ICT staff can manage users, policies, devices, and incidents without direct database edits |
| Reliability    | WAN outages, failed APs, and unavailable application services generate useful alerts                  |

## 11. Immediate next steps

The highest-value next move is not to start rewriting the frontend. It is to finish the hardware and code inventory so the software architecture matches what can actually be deployed.

I recommend doing these tasks in order:

1. Inventory the hardware. Record model numbers and take photos of the labels on the routers, switches, outdoor units, and APs.
2. Map the buildings and links. Identify which locations are connected by LAN cable and which rely on outdoor wireless bridges.
3. Verify the current deployment. Establish whether FreeRADIUS and CoovaChilli are running, where they run, and which parts of the existing Zyranet code are operational.
4. Measure the current network. Record Starlink performance, link speeds, and the busiest areas.
5. Finalize the target topology and procurement list. Buy only the equipment that closes a verified gap.
6. Start the repository migration. Build the identity and policy model, remove payment coupling, and introduce tests before replacing the current dashboard.

One final technical point: the current repository is a useful starting point, but the inspection so far is not a full audit of every file or a live test of the network. The next implementation pass should examine the remaining security code, RADIUS configuration, captive-portal configuration, frontend JavaScript, and deployment scripts before any production migration.

My recommendation: stabilize the network first, make school identity and access the core of Zyranet second, and build the polished operations interface on top of those foundations. That gives you a credible system for the school without wasting the hardware and software work you have already invested.