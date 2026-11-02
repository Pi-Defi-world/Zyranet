ZYRANET CAMPUS CONNECTIVITY
Technical Master Architecture, Recovery, Configuration & Implementation Manual

Akwa Ibom State University of Education (AUE)
Centre for Educational Technology  |  ICT Infrastructure Unit
Version 2.0 — Working Draft for technical validation and management review
Prepared: 30 October 2026

Document control
Field
Value
Institution
Akwa Ibom State University of Education (AUE)
Owner
Centre for Educational Technology / ICT Infrastructure Unit
Version / status
2.0 — Engineering working draft; not yet an as-built record
Planning basis
Existing mixed-vendor network; two accessible Starlink connections; recovered legacy devices
Population planning context
Approximately 3,000+ students and 400+ staff; simultaneous active demand must be measured
Commercial model
Free campus internet access to users; school-funded Zyranet service subscription (TBD)
Approval
Management / Vice-Chancellor approval and ICT sign-off required


Important: This manual is deliberately optimistic about reuse, but it does not invent exact device models, radio pairings, cable routes, distances, firmware versions, measured throughput or supplier quotations. These are field-capture items. The first implementation phase turns this working design into the verified as-built design.
How to use this manual
Use the phases in order. Do not begin broad configuration changes before the inventory, backup and topology capture are complete.
Treat every old device as potentially reusable until a repeatable test demonstrates a fault or incompatibility.
Where a field is marked TBD, capture the real value during the site survey. Do not substitute a guess.
Keep the technical design vendor-neutral. Ubiquiti, TP-Link, D-Link, Cisco and other devices may coexist.
Keep the school-facing proposal aligned with this document. Scope changes must be reflected in both.
Contents
1. Project intent and design principles
2. Confirmed facts, assumptions and unknowns
3. Existing asset baseline and site map
4. Target architecture
5. Physical recovery and as-built discovery
6. IP addressing, routing and segmentation
7. Two-Starlink WAN design and ISP options
8. Wireless backhaul and building access
9. Power, solar, UPS and electrical integration
10. Zyranet software architecture
11. Device integration and monitoring
12. Identity, access and traffic policy
13. Detailed implementation phases and procedures
14. Testing, acceptance and handover
15. Operations, maintenance and incident response
16. Security and privacy
17. Bill of quantities and cost model
18. Staffing, responsibilities and service subscription
19. Risk register
Appendices: field forms, configuration templates and source notes
1. Project intent and design principles
The project is to restore, connect and progressively improve the University's existing campus network using the equipment already owned and recoverable. The objective is a connected, supportable campus—not a wholesale replacement exercise and not an Omada-only network.
Reuse-first: recover the old network's working topology and roles before proposing replacements.
Two confirmed accessible Starlink services are the initial WAN baseline. The school may own about five terminals, but only two are currently in project access and budget scope.
Other ISPs, including Airtel ODU and dedicated fibre/leased-line services, are optional candidates only after coverage, pricing and service tests.
Vendor-neutral control: Zyranet records and integrates device capabilities rather than assuming a single controller can configure all vendors.
Graceful degradation: internet forwarding should continue during a Zyranet dashboard or monitoring outage wherever the configured gateway and access design permit it.
Priority by institutional need: exams, administration and teaching systems receive protected policy treatment; general student access remains fair and usable.
Free campus access: students, staff and guests are not charged for general campus internet. Creative Zone is not to be treated as a paid internet tier.
Measure before buying: purchases are approved only against a documented gap, failed test or capacity trigger.
2. Confirmed facts, assumptions and unknowns
Item
Current project position
Treatment
Population
3,000+ students and about 400+ staff (planning context)
Use for demand planning; measure active concurrency
Internet
Two Starlink connections can be accessed now; school reportedly has about five
Design initial WAN around two; other terminals are out of scope until access is granted
Legacy devices
Recovered list includes Ubiquiti, D-Link, TP-Link/CPE, dishes, transmitters, receivers and indoor units
Assume potentially serviceable; inspect and test in place or on bench
Campus locations
School of Science (water tank, arms 1/2, central hub), Primary Education, Provost/Masspool, Library, former Directorate of Degree, Student Affairs, Mathematics, ICT
Confirm official building names, exact coordinates, rooms and link endpoints
Exact models / revisions
Not fully recorded
Capture label, MAC, serial, hardware revision, firmware and power requirement
Radio pairings
Not fully established in inventory
Discover and confirm each transmitter-to-receiver association
Distances / line of sight
Not supplied
Measure or map after site walk; do not assume a link budget
Switching
Some control switches noted; managed capability unknown
Test VLAN, trunking, PoE and management support individually
Cabling
Existing runs are to be recovered and tested
Test each run; re-terminate before replacing where appropriate
Power
UPS and solar/inverter work required; Hall A needs electrical and longer-runtime attention
Measure loads and existing battery/inverter condition before sizing
Gateway
ER7206 appears in earlier design but installation/ownership not verified
Treat as candidate, not confirmed installed asset
Zyranet
Existing FastAPI/PostgreSQL application; current production deployment requires code and deployment audit
Preserve useful modules; refactor incrementally


3. Existing asset baseline and site map
The separate legacy inventory contains the following observations. The names below are retained as supplied; spelling and site naming must be confirmed during the walk-through.
Location / label in inventory
Recorded equipment / connection notes
Field action
School of Science — on the water tank
2 outdoor units with a receiver; 2 outdoor receivers
Identify all four units; determine which are radios, antennas or receiver assemblies; record MACs and pairings
Primary Education
Lab computer indoor unit connecting to School of Science outdoor unit / HOD office
Trace cable from indoor unit; identify remote radio and exact HOD office endpoint
School of Science — Arm 1
1 D-Link indoor unit
Record model, role, uplink and management address
Downstairs
3 D-Link indoor units; A office has a control point
Identify control point; map each unit to its cable and served area
Masspool at Provost Office
2 Ubiquiti receivers; 1 large transmitter; 2 P2P transmitters
Recover configuration and establish intended radio topology
Library
1 D-Link indoor unit downstairs
Trace uplink and served coverage
Central Hub — School of Science
2 D-Link indoor units; 1 control switch in office; Arm 2 is described as replica of Arm 1; Primary Education HOD office / indoor unit in upstairs lobby computer lab
Confirm which indoor units are local distribution versus client APs; verify Arm 1/2 relationship
Former Directorate of Degree
1 outdoor pool transmitter; 1 CPE610; 1 CPE510; 4 square transmitters; 2 C-Spain dishes; 1 stainless dish (record incomplete)
Photograph each item and labels; identify make/model and whether passive antenna or active radio
Student Affairs
1 outdoor unit
Identify model, link partner and powered location
Mathematics Department
2 dishes
Determine whether dishes are antennas only or complete radio assemblies
ICT
Not included in inventory
Add ICT room, core equipment, WAN and all endpoints to survey


The inventory is not yet a complete bill of materials. It records observations, not verified device counts by model. The asset register must distinguish an active radio from an antenna/dish, injector, indoor power supply and receiver.
3.1 Site walk route and evidence capture
Start at the ICT/core location. Photograph Starlink terminals, gateway, switches, server/controller PC, UPS/inverter and all patching.
Visit each named building and trace each network cable from indoor unit to switch or computer, and each outdoor radio to its PoE injector and mast.
Photograph device labels close enough to read manufacturer, exact model, hardware revision, serial number, MAC address and power rating.
Record LED state, cable port, PoE injector model/voltage, mounting direction, antenna orientation and visible cable condition.
Ask local staff which areas the device served, what it connected to and what symptoms were seen before shutdown.
Record the other endpoint of each radio link. Do not mark a pair confirmed until both endpoints or a reliable configuration record support it.
Mark unknown links as unknown; do not connect two devices based only on similar appearance.
4. Target architecture
The target is a layered design. Exact physical placement is derived from the recovered topology and survey; the following is the functional arrangement.
Layer
Function
Initial implementation
WAN
Two independent Starlink internet feeds
Keep each terminal/router identifiable; test each separately; connect to multi-WAN-capable gateway or verified existing router arrangement
Edge gateway
Routing, NAT, firewall, DHCP, WAN health, traffic policy
Use an existing suitable gateway if verified; otherwise procure only the minimum gateway needed to safely combine two WANs
Core / distribution
Aggregate building links and carry network segments
Reuse existing switches and radio bridges; validate uplink speed, VLAN/trunk capability and power
Building backhaul
Move connectivity between campus sites
Restore existing Ubiquiti/D-Link/TP-Link/CPE links in their known roles; test throughput and stability
Building access
Connect phones, laptops and lab computers
Reuse indoor APs/units after checking mode, security and capacity
Services
Zyranet, database, DNS/DHCP/RADIUS as selected, monitoring
Host on a stable ICT machine/server; keep backups and UPS protection
Operations
Inventory, map, monitoring, alerts and policy interface
Zyranet provides a common operations view with vendor-specific adapters


4.1 Network flow
Starlink A ─┐
            ├─ Multi-WAN edge gateway ─ Core/distribution ─ Existing building backhaul ─ Building switches/APs ─ Users
Starlink B ─┘
                                      │
                                      └─ Services network: Zyranet / database / monitoring / authentication
The two Starlinks should normally be treated as two independent WAN circuits. A multi-WAN gateway can distribute separate sessions across both and fail over when one fails. It does not normally combine two Starlink links into one single 2×-speed connection for an individual download. True bonding requires a bonding service or tunnel endpoint and introduces cost, latency and operational complexity; it is not a Phase 1 requirement.
4.2 Proposed priority domains
Domain
Priority
Policy intent
Exams complex / examination systems
Critical
Protected minimum share where capacity allows; avoid bulk downloads; stable DNS and access to approved exam services
Administration buildings
High
Reliable access to institutional systems, email, records and video meetings
Teaching / labs / learning resources
High
Prefer academic and teaching applications; avoid unnecessary throttling
General student network
Normal / fair-share
Per-device or per-user fairness; reasonable per-client shaping; client isolation where supported
Guest
Low / restricted
Internet-only, time-limited where appropriate, no management or private server access
ICT management
Restricted / privileged
Management interfaces reachable only from authorised ICT workstations


5. Physical recovery and as-built discovery
5.1 Recovery rules
Do not factory-reset a radio, router or switch before recording its label, current configuration and known role.
Do not change a live radio's channel, frequency, SSID, encryption or IP while it may still carry a building link.
Preserve power injectors: passive PoE and 802.3af/at/bt are not interchangeable. Verify the voltage and pinout printed on the injector/device.
Do not connect unknown PoE injectors to unknown devices. Wrong voltage can destroy equipment.
Do not assume the management IP is the factory default. Record DHCP leases, ARP/neighbour tables and labels first.
Use a dedicated laptop and isolated test switch for bench recovery. Do not scan arbitrary campus or public networks.
5.2 Device recovery procedure
Assign a unique asset ID (e.g. AUE-SS-WT-RAD-01). Photograph the installed device, label, mount, cable route, injector and power source.
Record model, hardware revision, serial, MAC, firmware, power specification, observed role, location, link partner, cable ID and condition.
Before removal, record LED state and any visible signal/association information. Where possible export the current configuration.
Label both ends of every cable and label the PoE injector with the matching asset ID.
Bench test one device at a time using the correct power supply and an isolated laptop/switch. Check boot, Ethernet link, management access and reset behaviour without resetting.
Identify its mode: AP, station/client bridge, point-to-point bridge, router, switch, or unknown. Save a configuration backup if available.
Return a reusable device to the same known role first. Only redesign its role after the old network map is understood.
Record pass/fail evidence, test date and technician. A failed test must state the exact failure and test conditions.
5.3 Link verification
Identify both ends and record their MAC addresses, radio model, mounting location and direction.
Check that both ends use compatible frequency band, channel width, SSID/link identifier, security and bridge mode.
Record signal strength, noise floor, SNR, modulation/MCS, channel utilisation, link uptime and negotiated Ethernet rate where the device exposes them.
Run a controlled throughput test across the link using iperf3 between endpoints; record TCP and UDP results, packet loss and latency. Do not use internet speed tests to measure a single backhaul link.
Run a continuous ping and monitor for at least 30 minutes during commissioning; repeat during a busy period.
Confirm that the far building receives the expected DHCP address and can reach the gateway, DNS and internet.
Only mark a building path as verified when the full path works, not merely when the radio LEDs indicate association.
5.4 Cable testing
Give each cable run an ID and record source, destination, estimated length, indoor/outdoor exposure and cable category.
Disconnect equipment before cable testing. Use a wire-map tester to identify opens, shorts, reversals, split pairs and crossed pairs.
If a run fails, re-terminate both ends using the same wiring standard (T568B unless an existing documented standard requires otherwise), then retest.
If it still fails, inspect for water, crushed cable, poor joints or excessive length. Replace only the failed section/run.
Use solid-copper outdoor-rated cable for exposed PoE runs; avoid CCA. Keep Ethernet copper runs within the 100 m channel limit; use fibre or a wireless bridge for longer spans.
Record the test result and label both ends permanently.
6. IP addressing, routing and segmentation
Do not choose final subnets until existing device addresses and any institutional LAN ranges are collected. The plan below is a logical template, not an instruction to renumber everything on day one.
Network
Suggested VLAN ID
Purpose
Access policy
Management
10
Gateway, switches, radios, AP management
ICT-only; no student/guest access
Servers
20
Zyranet, database, monitoring, authentication services
Only required ports from approved networks
Administration
30
Admin offices and management users
Institutional resources and internet
Students
40
Student access
Internet and approved learning resources
Teaching / labs
45
Labs, teaching rooms and shared academic equipment
Academic services and internet
Exams
50
Exam complex and exam systems
Restricted, prioritised and tested before examination windows
Guest
60
Visitors
Internet-only and client isolation
Creative Zone
70
Creative Zone users and facilities
Separate policy; free campus connectivity; no paid internet assumption


If existing devices cannot carry VLAN tags, segmentation must be enforced at the nearest capable managed switch/router or by separate physical ports/bridges. An unmanaged switch is not a security boundary. Avoid sending VLAN trunks through an old device until its transparent VLAN behaviour has been tested.
6.1 DHCP and gateway ownership
Only one authorised DHCP server should serve a given broadcast domain unless a deliberate failover design exists.
Record the current DHCP server and subnet before changing anything. Rogue DHCP from old routers is a common cause of intermittent connectivity.
Use reservations or static addresses for infrastructure devices; document the address, device ID and owner.
Set gateway, DNS and DHCP options consistently. Avoid double NAT between Starlink routers, old TP-Link routers and the new edge gateway where possible.
Do not disable Starlink router functionality until the required bypass/bridge mode and recovery procedure are confirmed for the installed Starlink hardware.
7. Two-Starlink WAN design and ISP options
Initial service baseline: two accessible Starlink connections. The project does not assume that the other reported Starlink terminals are available. Confirm the service plan and actual monthly bill for each active terminal.
WAN option
Status in this project
Cost / commercial note
Decision
Starlink A
Confirmed accessible
User-reported current recurring fee: ₦57,000/month per service; verify each account invoice and plan
Use now
Starlink B
Confirmed accessible
User-reported current recurring fee: ₦57,000/month per service; verify each account invoice and plan
Use now
Starlink terminals beyond the two
Reported school assets, access not confirmed
No cost included until access and account ownership confirmed
Do not rely on them
Airtel SmartConnect 5G ODU
Suggestion only; not confirmed available at the campus
Published launch reports listed ₦25,000 device/entry cost, ₦25,000/month up to 50 Mbps or ₦45,000/month up to 100 Mbps; verify current offer, coverage and actual signal on site
Optional pilot only
Airtel dedicated internet / fibre / leased line
Potential institutional ISP enquiry; availability not confirmed
Airtel advertises dedicated symmetric bandwidth and SLA options but requires a site-specific quotation; public page does not publish campus pricing
Request formal quote
Local fibre ISP
Potential candidate; not yet selected
Enquire for serviceability, contention, SLA, installation, static IP and monthly fee
Request at least 2 quotes


7.1 WAN commissioning
Record Starlink terminal ID, account owner, plan, router model, power supply, installation coordinates, cable length and obstruction status.
Connect Starlink A alone to a test laptop or gateway. Measure download, upload, latency, jitter and packet loss at morning, midday, evening and peak period.
Repeat the same test on Starlink B using the same test device and location where possible.
Record 7 days of baseline results if operationally possible. A single speed test is not a capacity plan.
Connect both WANs to the multi-WAN gateway. Configure health checks to more than one stable external destination and set failover thresholds.
Test load distribution with multiple simultaneous sessions; test failover by disconnecting WAN A and WAN B separately.
Verify that existing sessions may reset when a WAN fails over. Document this expected behaviour.
Set per-network policies and monitor actual WAN utilisation before deciding whether to buy additional internet.
7.2 Capacity model
The university population is approximately 3,400 people (3,000+ students and 400+ staff). That does not mean 3,400 people are simultaneously active. However, a literal guarantee of 10 Mbps to every person at once would require at least 34 Gbps of aggregate internet capacity before overhead. Two Starlinks will not deliver that guarantee. The initial target must therefore be described as a fair-share service with a configurable per-active-device ceiling, not a guaranteed 10 Mbps to every registered person.
Measure associated devices, active clients, busy-hour traffic and top applications separately.
Set an initial conservative per-device rate policy only after measuring each WAN and local radio capacity.
Give exams, administration and teaching systems priority through supported gateway QoS and segmentation.
Apply fairness so one device cannot consume the whole link. Use per-user identity where available; otherwise per-device controls are an interim approximation.
Review the policy weekly during the pilot. Publish the actual service expectation rather than advertising a guaranteed 10 Mbps if the capacity cannot sustain it.
8. Wireless backhaul and building access
The existing radio infrastructure is presumed to have been selected for building-to-building connectivity. The first goal is to restore those paths, not replace them. Record every radio's intended role and link partner.
Use dedicated bridge radios for backhaul where the existing topology supports it; do not repurpose a building access AP as a backhaul without testing the effect.
Check line of sight, Fresnel clearance, mount stability, water ingress, lightning protection, earthing and cable condition.
Keep radio management addresses in the management network where supported.
Use unique credentials; disable unused services and remote management from student networks.
Use the least disruptive channel and channel width that gives stable performance; record the chosen values.
Where equipment is old but working, preserve the known stable configuration first. Tune only after baseline throughput and interference measurements.
9. Power, solar, UPS and electrical integration
Power is part of the network path. A powered-down receiver, PoE injector or building switch disconnects a building even when the central Starlink and gateway remain online. Hall A is included in the coverage objective; its electrical/roof work and additional solar/inverter capacity must be planned as a coordinated building-readiness workstream.
9.1 Load and runtime survey
Record the wattage from the label of each Starlink power supply, gateway, switch, PoE injector, server, radio and AP. Use a plug-in power meter where practical.
Record inverter model, battery chemistry, nominal voltage, Ah/kWh rating, age, panel capacity, charge controller and existing loads.
Separate critical network loads from general building loads. Do not add fans, lights or unrelated sockets to the network UPS budget.
Calculate required battery energy from measured watts and required runtime. Include inverter efficiency, battery depth-of-discharge limits and ageing margin.
Have a qualified electrician inspect mains circuits, earthing, surge protection, changeover and solar/inverter installation.
Test actual runtime under the real network load and record the result.
9.2 Power distribution requirements
Protect both Starlink power supplies, gateway, core switch, essential PoE feeds and Zyranet server/controller.
Protect critical building radio/switch/AP power at priority locations; document which buildings have local backup.
Use correctly rated PoE injectors and surge protectors on outdoor Ethernet runs.
Provide proper mast and equipment earthing. Do not improvise mains wiring.
Ensure battery banks use compatible batteries of the same chemistry, voltage, capacity and age; do not mix new and degraded batteries.
Create a safe shutdown procedure for server/database equipment if runtime is nearly exhausted.
10. Zyranet software architecture
Zyranet is the university's network operations, identity and access-policy platform. It is not a replacement for all vendor controllers and it must not pretend to have telemetry that a device does not expose.
Module
Responsibilities
Initial priority
Inventory
Devices, models, serials, MACs, locations, roles, firmware, capability flags, warranty/condition
P0
Topology
Buildings, links, endpoints, confidence, dependency graph, physical/logical distinction
P0
Discovery
ARP/neighbour, DHCP leases, ping, TCP probes, SNMP and vendor APIs where available
P0
Monitoring
WAN checks, gateway health, device reachability, interface counters, link metrics where exposed
P0
Incident management
Alert, affected buildings, timeline, acknowledgement, resolution and evidence
P0
Identity
Students/staff/guests/admins, groups, status and import/sync
P1
Access policy
Role/network policy, guest expiry, schedules, rate policy and enforcement status
P1
RADIUS integration
Authentication/accounting if the chosen AP/gateway supports the selected method
P1
Configuration records
Config backups, change plan, approval, execution record and restore notes
P1
Reports
Availability, WAN usage, incidents, authentication, audit and monthly service report
P2


10.1 Device adapter model
Implement an adapter per vendor/protocol, not one universal device driver. Each adapter declares what it can actually do.
Adapter type
Read capability
Write capability
SNMPv2c/v3
System name, uptime, interface state/counters, selected sensors
Usually none initially; SNMP writes disabled
Ubiquiti airOS / airMAX
Model-dependent status, association, signal, uptime and configuration fields
Only model/firmware-specific actions after backup and approval
TP-Link / D-Link
Model/API/SNMP dependent inventory and interface state
Only where a supported interface exists
Cisco
SNMP, SSH/CLI, LLDP/CDP where enabled
Template-based CLI only after model and IOS validation
Generic web-only
Reachability, TLS/HTTP response, manual evidence
Guided operator action; no blind automation
Unmanaged / unsupported
Reachability and neighbouring switch observations
No direct configuration


Never store plaintext device passwords in source code or logs. Use a secrets store or encrypted runtime configuration. SNMPv3 is preferred where supported. If legacy SNMPv2c is necessary, restrict it to the management network and use a unique non-default community.
10.2 Suggested Zyranet data entities
sites, buildings, floors, rooms, racks and power zones
devices, device_models, device_interfaces, device_addresses, device_credentials_reference
links, link_endpoints, link_measurements, topology_observations
wan_circuits, wan_measurements, gateway_health
discovery_jobs, discovery_observations, monitoring_checks, incidents, alert_events
users, roles, groups, user_group_memberships, access_policies, policy_assignments
radius_sessions, auth_events, guest_access_records
configuration_snapshots, change_plans, change_jobs, audit_events
service_subscriptions, service_reports and support_cases
10.3 API boundaries (proposed)
Area
Example endpoints
Inventory
GET/POST /api/devices; GET/PATCH /api/devices/{id}; POST /api/devices/{id}/inspect
Topology
GET/POST /api/topology/buildings; GET/POST /api/topology/links; POST /api/topology/discover
Discovery
POST /api/discovery/jobs; GET /api/discovery/jobs/{id}; GET /api/discovery/observations
Monitoring
GET /api/monitoring/summary; GET /api/monitoring/wan; GET /api/monitoring/devices; GET /api/alerts
Incidents
POST /api/incidents; PATCH /api/incidents/{id}; GET /api/incidents
Identity
POST /api/users/import; GET/POST /api/users; PATCH /api/users/{id}/status
Policies
GET/POST /api/policies; POST /api/policies/{id}/assignments; GET /api/policies/{id}/status
Configuration
POST /api/devices/{id}/snapshots; POST /api/change-plans; POST /api/change-plans/{id}/approve
Reports
GET /api/reports/availability; GET /api/reports/usage; GET /api/reports/audit


11. Identity, access and traffic policy
Initial account source: controlled CSV import of student/staff records; EduAdmin integration can follow after the data contract and API availability are confirmed.
Each staff/student account must have a stable institutional identifier, status and group. Avoid using a shared universal password.
Guest access should be sponsored or approved, time-limited and internet-only.
Select captive portal or WPA-Enterprise only after testing the installed access points/gateway and RADIUS compatibility. Do not assume every legacy AP supports 802.1X.
Where older APs cannot enforce identity or VLAN assignment, apply access control at a capable gateway or use a separate SSID/physical segment where possible.
Document behaviour during RADIUS/Zyranet outage: existing sessions, new authentication, emergency access and expiry. Do not silently fail open.
Free campus internet is the policy. Zyranet is funded through an institutional service subscription (TBD), not end-user payment.
12. Detailed implementation phases and procedures
Phase / duration
Work performed
Exit evidence
Phase 0 — Authorisation and mobilisation (1–3 working days)
Confirm project sponsor, ICT lead, outage authority, access to two Starlinks, safe working-at-height approval, asset custody and procurement approval.
Signed scope; named project team; access to ICT rooms; work windows; asset register opened.
Phase 1 — Physical audit and legacy recovery (5–10 working days)
Walk every location; photograph and label every device/cable/injector; recover configuration backups; identify model/revision/MAC; bench-test suspect equipment; trace radio pairs; record power loads and existing UPS/solar assets.
Complete asset register; link-pair register; site plan; cable test log; device test evidence; unknowns list; no unapproved resets.
Phase 2 — Restore the existing network path (5–10 working days)
Start at ICT/core; verify each Starlink separately; verify gateway and DHCP; restore one known building path at a time; test radio association and throughput; reconnect building switches/APs; test end-to-end access.
At least one stable core-to-building path; no rogue DHCP; measured WAN and backhaul baseline; rollback notes.
Phase 3 — Stabilise gateway and two-WAN service (3–7 working days)
Select/verify multi-WAN gateway; connect WAN A/B; configure health checks, failover and policy routing; configure firewall and DHCP; test failover and session behaviour; document WAN performance.
Both Starlinks usable; failover test evidence; network policy and IP plan approved.
Phase 4 — Power and cabling remediation (Parallel, 1–3 weeks depending on faults)
Test and re-terminate existing runs; repair only failed runs; measure protected loads; repair suitable UPS units; size batteries/inverter/panels for critical loads and Hall A; install surge/earthing with qualified personnel.
Cable logs complete; power runtime tested; Hall A power scope and readiness signed off.
Phase 5 — Zyranet operations MVP (2–4 weeks, parallel with physical work)
Audit current repository; fix authentication/secrets; version database migrations; build inventory, building/link topology, discovery, WAN/device health, incidents, audit and basic dashboard; add read-only adapters first.
ICT can see verified devices, links, WAN state and incidents; data labelled live/stale/unavailable; backups and restore tested.
Phase 6 — Access policy and pilot (2–3 weeks)
Choose compatible captive portal/RADIUS or supported enterprise Wi-Fi method; import pilot users; create staff/student/guest groups; apply policy on a test segment; test account disable and outage behaviour.
Pilot users authenticate; isolation tests pass; no end-user payments; emergency access process documented.
Phase 7 — Priority networks and campus rollout (2–4 weeks depending on buildings)
Introduce exams/admin/teaching policy domains where hardware supports them; extend restored building paths; verify coverage and client load; tune rate limits; train ICT operators.
Named buildings pass connectivity tests; exams/admin priority verified; load tests and operations handover complete.
Phase 8 — Capacity optimisation and ISP procurement (After 2–4 weeks of measurement)
Compare both Starlinks; collect peak utilisation; test optional Airtel ODU only if coverage exists; obtain institutional ISP/fibre quotations; compare SLA, throughput, installation and monthly cost; procure only if trigger met.
Documented WAN decision, quote comparison and management approval.


12.1 Day-by-day field workflow for the first audit
Day
Work
Required output
Day 1
ICT core room and Starlink A/B; gateway, switches, servers, power; photograph and label
Core rack diagram; WAN IDs; device and power list
Day 2
School of Science water tank, central hub, Arms 1 and 2; trace outdoor/indoor radio endpoints
School of Science topology and radio-pair table
Day 3
Provost/Masspool and former Directorate of Degree; trace Ubiquiti/CPE/dish assemblies
Provost and former Directorate topology
Day 4
Primary Education and Library; trace indoor units and computer lab links
Building connection map
Day 5
Student Affairs, Mathematics, ICT and Hall A; inspect power and coverage needs
Remaining asset list; Hall A power/coverage scope
Day 6
Bench tests, cable tests, configuration exports and link measurements
Pass/fail matrix; backup archive; remedial list
Day 7
Reconcile map with ICT staff; verify unknown pairings; produce as-built v1 and gap list
Signed audit report and Phase 2 work order


12.2 Standard change procedure
Create a change ticket with affected building, devices, reason, expected outcome, risk and outage window.
Capture current config, screenshots, interface counters, IP settings and known-good connectivity test.
Prepare exact changes and rollback steps. Peer-review where possible.
Notify affected users and ICT lead. Confirm physical access to the device before changing it.
Apply to one device/link at a time. Do not change both ends of a critical radio link simultaneously unless the planned process requires it.
Verify management access, link association, end-to-end IP, DNS, internet, expected policy and monitoring.
If verification fails, execute the rollback or isolate the failed change and restore the last known-good configuration.
Close the ticket with timestamps, operator, evidence, final configuration reference and follow-up.
13. Testing, acceptance and handover
Test
Pass condition / evidence
WAN A and WAN B
Independent speed/latency/packet-loss baselines at multiple times; both pass through gateway
WAN failover
Disconnect each WAN in turn; other WAN carries new sessions; event logged; recovery verified
Building backhaul
Each path has identified endpoints, measured throughput, latency/loss, signal metrics where available and 30-minute stability test
Cabling
Each active run has wire-map pass, ID, source/destination and label
DHCP / addressing
One intended DHCP authority per segment; correct gateway/DNS; no rogue leases
Coverage
Required rooms/buildings pass agreed Wi-Fi signal and application tests; survey evidence retained
Priority policy
Exams/admin/teaching test traffic receives intended policy treatment under load
Security isolation
Student/guest cannot reach management interfaces or protected server ports
Zyranet outage
Internet forwarding and existing sessions behave as documented; dashboard failure does not shut down routing
Authentication
Student, staff, guest and admin flows work; disabled user loses future access; session termination tested where supported
Power
Critical loads run for approved runtime; switchover and restoration tested
Restore
Database, Zyranet configuration and device configuration backups restored in a test environment
Load
Representative concurrent-user test records latency, throughput, packet loss, CPU, memory and first bottleneck


13.1 Capacity test design
Do not simulate 3,400 full-speed users unless the test platform and WAN capacity are designed for it. Begin with staged loads (25, 50, 100, 200, 300 clients) and increase safely.
Separate Wi-Fi association capacity from WAN capacity. A client can be connected but idle.
Use iperf3 on the campus LAN to test wired/radio throughput independently from Starlink.
Use controlled internet test traffic and monitor WAN usage, gateway CPU, AP airtime, radio retransmissions and switch uplinks.
Record the number of active test clients, application mix and test duration. Report measured outcomes rather than a blanket speed guarantee.
14. Operations, maintenance and incident response
Cadence
Task
Daily
Review WAN status, gateway reachability, critical radio/AP outages, server health and open incidents
Weekly
Review peak-hour WAN utilisation, building link performance, authentication failures and repeat incidents
Monthly
Export database/device backups; review accounts; test selected restore; report availability and capacity
Quarterly
Review firmware/security advisories; test UPS runtime; inspect masts, earthing and outdoor cable condition
Before exams
Freeze nonessential changes; test exam network, power, DNS, priority policy, backup WAN and incident escalation


14.1 Incident triage sequence
Establish scope: one user, one AP, one building, multiple buildings or whole campus.
Check power and physical link first: UPS/inverter, PoE injector, switch port, cable and radio power.
Check topology dependencies: is the affected building's upstream radio/switch reachable?
Check gateway and WAN separately: can the gateway reach the internet through Starlink A/B?
Check DHCP, DNS and authentication. Distinguish 'connected to Wi-Fi' from 'has a valid IP' and 'has internet'.
Record incident timeline, affected assets, tests, changes and resolution in Zyranet.
15. Security and privacy
Use unique administrator accounts, MFA where possible, role-based access and token revocation.
Correct any insecure authentication logic in the existing application before production use; never accept substring or partial password matches.
Keep secrets out of source code, Docker images, logs and shared documents. Rotate exposed defaults.
Restrict management interfaces to the management network and authorised ICT workstations.
Use HTTPS for portal and admin traffic. Restrict CORS and apply rate limits.
Encrypt database backups and configuration exports; keep an off-device copy and test restoration.
Collect only the student/staff identity and network accounting data needed for the service; define access and retention rules with the University's data-protection function.
Do not expose raw student browsing histories to ordinary operators. Define a lawful, documented incident process.
16. Bill of quantities and cost model
This is a procurement control schedule, not a claim that every line must be purchased. Quantities are determined by the audit. All local hardware, solar, cabling and labour prices must be obtained through dated quotations. Do not convert unknown quantities into a false total.
Cost item
Quantity basis
Budget treatment / price
Starlink A subscription
1 active account
₦57,000/month each (user-reported; verify invoice/plan)
Starlink B subscription
1 active account
₦57,000/month each (user-reported; verify invoice/plan)
Second/other school Starlinks
Only if access and active accounts confirmed
₦0 in current baseline; TBD if activated
Multi-WAN gateway
1, only if existing gateway cannot safely support 2 WANs and required policy
TBD — model and local quotation after audit
Managed core switch
Only if existing core switch fails required port/VLAN/uplink tests
TBD — quantity and model after audit
Building managed switches
Only where a building requires VLANs/PoE/management and existing switch cannot provide it
TBD per building
Access points
Only where measured coverage/capacity gap exists
TBD per room/building; reuse first
Radio replacements
Only after device fails testing or cannot meet required link performance
TBD per failed link; reuse existing radio pairs first
Outdoor Cat5e/Cat6 solid-copper cable
Measured failed/exposed runs + 10% slack
TBD per metre; no blanket replacement
RJ45 plugs/boots/keystones/patch cords
Measured ports + 15–20% spares
TBD by pack/quantity
Crimping tool and wire-map cable tester
1 field kit
TBD — obtain 2–3 local quotations
Punch-down tool / patch panel / rack accessories
As required by existing termination condition
TBD
PoE injectors / surge protectors
Only matching device standards and outdoor runs
TBD per unit
UPS battery replacement
Only UPS units whose electronics pass test
TBD by voltage, chemistry and Ah
New UPS / DC mini-UPS
Measured load and runtime gap
TBD
Solar panels / inverter / batteries for Hall A and core
Measured energy budget and desired runtime
TBD after electrical design and site quote
Earthing, lightning and surge protection
Every exposed mast/run; design by qualified personnel
TBD
Installation consumables, labels, conduit, clips
Measured routes and actual work
TBD
Network engineer / field technician labour
Days, team size, travel, access equipment and scope
TBD — request itemised professional quotation
Electrical/solar contractor
Survey, design, installation, test and certification
TBD — separate qualified contractor quote
Zyranet implementation
Discovery, integrations, software, deployment, training and documentation
TBD — project implementation fee
Zyranet service subscription
Institutional annual/monthly support, hosting/maintenance, monitoring and updates
TBD — school-funded service subscription
ISP alternative pilot
Only after coverage and trial test
Airtel ODU public launch reports: ₦25,000 entry/device, ₦25,000/month up to 50 Mbps or ₦45,000/month up to 100 Mbps; confirm current terms and on-campus coverage
Dedicated ISP/fibre
Request site-specific institutional quote
TBD; SLA, committed bandwidth, install, router, static IP and recurring fee must be itemised


16.1 Known recurring WAN baseline
Recurring item
Monthly amount
Annualised amount
Starlink A
₦57,000
₦684,000
Starlink B
₦57,000
₦684,000
Two accessible Starlinks total
₦114,000
₦1,368,000


The Starlink figure is based on the user's current stated price and is consistent with Starlink Nigeria's public page showing residential service starting at ₦57,000/month. Confirm the actual account plan and invoice because Starlink plan prices and eligibility can change.
16.2 Quotation instructions
Obtain at least three quotations for material procurement where practical; quote must show make/model, specification, quantity, unit price, VAT, delivery, warranty and validity date.
Require the contractor to separate labour, transport, access equipment, consumables, testing and taxes.
Require solar/electrical quotations to show load calculation, panel wattage/count, inverter rating, battery chemistry/capacity, protection devices, expected runtime and warranty.
Require ISP quotes to show committed versus advertised bandwidth, upload/download, contention, SLA, uptime, support escalation, installation and monthly recurring fee.
Do not approve a hardware purchase without linking it to a failed test, measured capacity bottleneck, safety requirement or approved new coverage area.
17. Staffing, responsibilities and service subscription
Role
Minimum responsibility
Commercial treatment
Project/network lead
Own topology, design decisions, change control, acceptance and handover
Professional service fee — TBD
Senior network engineer
Gateway, routing, WAN, VLANs, radio links, security and performance tests
Day rate / fixed work package — TBD
Wireless/radio technician
Mast inspection, alignment, PoE, radio pairing, signal and link tests
Per day/link — TBD
Structured cabling technician
Cable tracing, termination, testing, labels and patching
Per run/day — TBD
Electrical/solar contractor
Load assessment, UPS/inverter/panel/battery work, earthing and safety
Separate quotation — TBD
Zyranet developer
Software audit, modules, integrations, deployment, migration, training
Implementation fee — TBD
ICT operator(s)
Daily operations, account lifecycle, incident response and records
University staff assignment
Project coordinator / safety support
Access approvals, outage notices, logistics and working-at-height controls
University/contractor assignment


Zyranet commercial model: the University subscribes to Zyranet as an institutional service. The subscription may cover software maintenance, security updates, monitoring integration, support, backups, periodic reporting and agreed development/upgrade allowance. It is not a payment collected from students for internet access. Pricing is TBD and should be agreed as a separate service schedule with service levels, support hours, response targets, renewal and exit/data-export terms.
18. Risk register
Risk
Impact
Mitigation / trigger
Unknown device models or hidden faults
Medium/high
Inventory and bench-test; retain replacement as contingency only
Radio endpoints incorrectly paired
High
Trace both ends; verify config and link metrics before changes
Only two of five reported Starlinks accessible
High
Plan for two; treat others as unavailable until written access and account details are supplied
WAN capacity below demand
High
Fair-share QoS; priority policies; measure peak load; procure additional ISP only with evidence
Unstable power at remote buildings
High
Measure local loads; backup critical radio/switch/AP; test runtime
Legacy devices cannot enforce VLANs
Medium
Enforce segmentation upstream or physically; replace only the limiting device if necessary
Zyranet outage affects access
High
Keep forwarding independent; test RADIUS/captive portal outage policy and emergency access
Uncontrolled configuration changes
High
Backups, approval, one-change-at-a-time and rollback
Outdoor lightning/water damage
High
Earthing, surge protection, UV cable, inspection
Budget overrun from premature purchases
High
Reuse-first procurement gate and itemised quotes
Privacy/security exposure
High
Least privilege, retention policy, encryption, audit and restricted management


Appendix A — Device asset register fields
Field
Example / instruction
Asset ID
AUE-LOC-TYPE-001
Location
Building / floor / room / mast
Vendor / exact model / hardware revision
Photograph label; do not enter just 'Ubiquiti'
Serial / MAC
Record each interface MAC if multiple
Firmware
Version/build/date if visible
Role / link partner
AP, station, bridge, router, switch; partner asset ID
Power
Voltage, PoE standard/pinout, injector model and watts
Management
IP, protocol, port, credential reference (never password in register)
Physical state
Mount, cable, weather, corrosion, water, LED
Bench / link test
Pass/fail with timestamp and evidence
Disposition
Reuse / repair / cannibalise / dispose after approval


Appendix B — Link register fields
Field
Record
Link ID
Unique identifier
A endpoint / B endpoint
Asset IDs and exact locations
Link type
Wireless PtP / PtMP / copper / fibre
Radio parameters
Band, channel, width, SSID/link ID, security mode
RF measurements
RSSI, noise, SNR, MCS, CCQ/retries where exposed
Performance
TCP/UDP throughput, RTT, packet loss, test duration
Power and cabling
Injector, PoE, cable ID, surge/earth
Status
Unknown / observed / associated / verified end-to-end


Appendix C — Zyranet repository work sequence
Freeze and back up the current repository and production database; document current deployment before code changes.
Audit main branch, dependencies, routers, database schema, Docker Compose, RADIUS and captive-portal deployment. Reconcile README claims with actual services.
Fix authentication flaws, default secrets, CORS, token lifecycle and admin roles before exposing new functions.
Introduce versioned database migrations; preserve device inventory, sightings and topology; migrate payment-related data only after dependencies and retention are understood.
Build inventory/location/topology data model first. Do not implement broad device configuration automation in the MVP.
Implement read-only discovery and monitoring adapters, with capability flags and source timestamps.
Add incident workflows and WAN reporting. Label every metric as live, stale, estimated or unavailable.
Add identity and access policies only after confirming the physical access equipment supports the chosen enforcement method.
Add write/configuration adapters only after read-only operation is reliable, backups are available and approval/rollback controls exist.
Appendix D — External pricing and verification sources
Starlink Nigeria residential pricing page: https://www.starlink.com/ng/residential — public page displayed service starting at ₦57,000/month and hardware starting at ₦318,000 in selected areas; the project uses the user's stated ₦57,000 per currently active service pending invoice verification.
Airtel SmartConnect 5G ODU launch pricing was reported by BusinessDay on 18 September 2025: https://businessday.ng/technology/article/airtel-nigeria-launches-smartconnect-5g-odu-router-to-expand-broadband-access-nationwide/ — ₦25,000 entry price, 50 Mbps plan ₦25,000/month, 100 Mbps plan ₦45,000/month at launch. This is an optional suggestion, not confirmed campus coverage or a current binding quote.
Airtel Nigeria Dedicated Internet: https://www.airtel.com.ng/ng/business/dedicated-internet — service tiers and dedicated symmetric bandwidth are described; price is quote-based.
NCC approved operator bundle plans: https://ncc.gov.ng/approved-operator-bundle-plans — published Airtel router bundle examples are not equivalent to a guaranteed campus leased line.
All supplier prices must be re-quoted at procurement date. No local hardware or labour price has been fabricated in this document.
End of technical working draft. This document becomes the as-built master only after Phase 1 field verification and ICT sign-off.
19. Zyranet software engineering blueprint
This section specifies the recommended implementation stack and the order in which the software is to be built. The objective is to extend the existing Zyranet repository, not to discard a working codebase and start again. The existing repository is understood to use Python/FastAPI, PostgreSQL, a static HTML admin interface and existing device/network discovery scaffolding. Before implementation, the developer must verify the current main branch, dependencies, deployment and schema.
19.1 Languages and technology choices
Layer
Selected language / technology
Why it is selected / implementation rule
Backend API
Python 3.12+; FastAPI
Continue the existing backend. Strong fit for APIs, network automation libraries and rapid integration.
API schemas / validation
Pydantic v2
Typed request/response contracts and validation at API boundaries.
Database
PostgreSQL
Keep the existing relational system of record; use explicit migrations.
ORM / database access
SQLAlchemy 2.x
Typed models and controlled queries; avoid mixing raw SQL patterns across modules.
Database migrations
Alembic
Every schema change is versioned, reviewed and reversible where practical.
Frontend
TypeScript + React + Vite
Build a maintainable operations dashboard with typed API contracts and reusable views.
Frontend styling
Tailwind CSS or existing design system
Choose one approach and standardise components; do not mix several UI frameworks.
API client
OpenAPI-generated TypeScript client or typed fetch wrapper
Keep frontend contracts aligned with FastAPI OpenAPI schemas.
Background jobs
Python worker process; start with database-backed job table and polling
Avoid adding Redis/Celery until measured job volume justifies it.
Network integrations
Python: httpx, pysnmp, scrapli/Netmiko where appropriate, Paramiko only when needed
Use protocol/vendor adapters. Start read-only; never run generic commands against unknown models.
Authentication
FastAPI security utilities; Argon2id/bcrypt password hashing; JWT or secure server sessions
Fix existing authentication flaws; enforce MFA for administrators where feasible.
Network authentication
FreeRADIUS, only after AP/gateway compatibility test
RADIUS is a separate service, not a Python replacement; Zyranet manages policy and integrations.
Deployment
Linux server (Ubuntu LTS), Docker Compose initially
Keep deployment reproducible; separate API, frontend/web server, PostgreSQL and optional worker.
Reverse proxy / HTTPS
Caddy or Nginx
TLS termination, routing and secure portal/dashboard delivery.
Testing
pytest, httpx TestClient, factory fixtures; Vitest + React Testing Library
Automated backend and frontend tests; hardware integration tests on a lab device.
Observability
Python logging with structured JSON; later Prometheus exporters if needed
Do not introduce a large monitoring stack before basic health and incident reporting work.
Version control / CI
GitHub; GitHub Actions
Lint, type checks, unit tests, migration checks and container build on every pull request.


Do not rewrite the backend in Go, Rust or Node.js for the first release. Those languages do not solve the hard problem, which is discovering and integrating heterogeneous legacy network devices. Python already fits the existing repository and has mature networking libraries. A future high-throughput collector can be separated only if profiling proves it necessary.
19.2 Repository structure to grow toward
zyranet/
  backend/
    app/
      main.py
      core/             # settings, security, logging, permissions
      api/v1/           # versioned API routers
      modules/
        inventory/      # devices, models, locations, interfaces
        topology/       # buildings, links, dependency graph
        discovery/      # scans, observations, identification
        monitoring/     # probes, metrics, alerts, incidents
        wan/             # Starlink/ISP circuits and health
        identity/        # users, groups, roles, lifecycle
        policies/        # access rules, rate policies, assignments
        integrations/    # vendor/protocol adapters
        audit/           # change and administrative events
      db/                # SQLAlchemy models, session, migrations
      workers/           # discovery and polling jobs
      tests/             # unit, API, integration
    alembic/
    pyproject.toml
  frontend/
    src/
      app/               # routing, app shell, auth state
      pages/             # dashboard, map, devices, buildings, users
      components/        # tables, forms, charts, status indicators
      features/          # inventory, topology, monitoring, identity
      lib/               # API client, types, formatting
    package.json
  deploy/
    compose.yaml
    Caddyfile
    env.example
    backup/              # backup and restore scripts
  docs/
    architecture/        # diagrams and decisions
    operations/          # runbooks and recovery procedures
    api/                 # API usage and examples
  scripts/
  README.md
The target structure is introduced incrementally. Do not move every existing file in one large refactor. First establish tests and module boundaries, then move one router/service at a time while keeping API compatibility where possible.
19.3 Software architecture and runtime services
Service
Runs as
Responsibility
Dependency / failure behaviour
Web frontend
Static build served by Caddy/Nginx
ICT dashboard and student/guest portal if required
Dashboard can be unavailable without stopping routing
FastAPI API
Container/service
Business rules, authentication, inventory, policies and reports
Must not directly perform long scans inside request handlers
PostgreSQL
Database service
Persistent records and job state
Backups; restore procedure; no public exposure
Discovery/monitor worker
Separate Python process
Scheduled probes, SNMP/API polling, discovery and report jobs
Can restart without losing job history
FreeRADIUS (conditional)
Separate service
Network authentication/accounting when selected access equipment supports it
Network access outage policy must be explicitly tested
Reverse proxy
Caddy/Nginx
HTTPS, routing, request limits and static frontend
Only public-facing entry point
Vendor adapters
Python package within worker initially
Read data from supported devices and later approved configuration
Adapter failure must not crash whole monitoring cycle

Incremental implementation note: the current code has a dedicated periodic
discovery worker, bounded CIDR expansion, persisted `discovery_runs`, and
sampled `device_sightings` linked to run/source/evidence. The observation feed
is still based on the worker host's neighbour table plus ICMP/TCP probes. It is
not authoritative client association, continuous device telemetry, or an
incident/alert system; those remain later implementation work. Scope entries
that are invalid, unsupported, or exceed configured caps produce partial runs
with an operator-visible explanation. On worker restart, sufficiently old
`running` records are closed as failed. Authenticated read-only history is
available in the Discovery dashboard; per-device sightings are sampled, while
run totals remain aggregate counts. Operator-triggered scans are persisted as
queued jobs and claimed by the same worker; a partial unique index prevents
more than one queued or running sweep at a time. The HTTP request never waits
for the network probes to complete. The initial hardware adapter is generic,
read-only SNMPv2c identity via the standard system MIB, restricted to configured
SNMP targets and audited; vendor-specific identification and interface polling
remain unimplemented. A single-device inspection is bounded and asynchronous,
but its result is not yet persisted as a separate inspection record.
The SNMP community defaults to empty and must be supplied through protected
runtime configuration or per-target configuration; network access should be
limited to a trusted management segment because SNMPv2c is not encrypted.


19.4 Core data model — implementation order
Order
Tables / entities
Key fields and relationships
1
sites, buildings, floors, rooms
Institution hierarchy; location IDs used by every device and link
2
device_models, devices, device_interfaces, device_addresses
Vendor, exact model/revision, serial, MAC, firmware, role, location, status, capability profile
3
links, link_endpoints, topology_observations
A/B device/interface endpoints, link type, confidence, discovered/verified status
4
wan_circuits, wan_measurements
Provider, circuit ID, terminal, plan, status, measured throughput/latency/loss, timestamps
5
discovery_jobs, discovery_observations
Scope, method, status, operator, evidence and timestamps
6
monitoring_checks, metric_samples, alerts, incidents
Check definition, value, severity, lifecycle, acknowledgement and resolution
7
users, roles, groups, memberships, auth_events
Institutional identifier, status, role and authentication audit
8
access_policies, policy_assignments, enforcement_results
Policy intent, target group/network, adapter, applied/failed/unverified state
9
configuration_snapshots, change_plans, change_jobs
Backup reference, diff, approval, operator, execution and verification
10
audit_events, service_subscriptions, support_cases
Administrative traceability, school service plan and support record


Every observation needs source, observed_at, last_success_at and confidence/state. A device must not be shown as definitively offline merely because one probe failed. Distinguish online, degraded, unreachable, stale, unknown and unsupported.
19.5 API design conventions
Use /api/v1 as the API prefix. Use plural resource names and stable UUID identifiers.
Use Pydantic request and response schemas; never expose ORM objects directly.
Use pagination for devices, observations, events and sessions.
Use consistent error responses: code, message, request_id and field_errors where relevant.
Protect write operations with role checks, CSRF protection where cookie sessions are used, rate limits and audit events.
Long-running work returns a job ID; the frontend polls GET /api/v1/jobs/{job_id} or receives updates later.
Document each endpoint in OpenAPI and add API tests before building the corresponding frontend page.
20. Exact Zyranet build phases and developer steps
The following is the recommended software delivery sequence. Each phase has entry requirements, implementation steps, outputs and a gate. A phase is not complete because code exists; it is complete when its tests and operational evidence pass.
Software Phase 0 — Repository and deployment audit
Entry: Before code changes.
Developer / implementation steps:
1) Clone and pin the current main branch
2) Record commit hash and Python/dependency versions
3) Inspect all routers, services, models/schema, frontend JavaScript, Docker Compose, RADIUS/CoovaChilli configuration and deployment scripts
4) Run the current application in a clean test environment
5) Document every currently working workflow and external dependency
6) Back up the production database and configuration
Deliverable: Repository audit, current-state architecture, reproducible development environment, backup and known-issues register.
Completion gate: Do not start destructive refactoring until current behaviour and backup restoration are verified.
Software Phase 1 — Security and engineering foundation
Entry: After Phase 0.
Developer / implementation steps:
1) Remove default secrets from code and create env.example
2) Fix exact password verification; use Argon2id/bcrypt hashes
3) Add admin roles and permission dependencies
4) Restrict CORS and trusted hosts
5) Add structured logging and request IDs
6) Add pytest and lint/type-check tooling
7) Add Alembic and baseline migration
8) Add CI pipeline and Docker health checks
Deliverable: Hardened login, roles, migration baseline, tests, CI and secure local deployment.
Completion gate: Security tests pass; database backup/restore demonstrated; CI green.
Software Phase 2 — Inventory and location model
Entry: After foundation.
Developer / implementation steps:
1) Design sites/buildings/floors/rooms
2) Add device model and device tables
3) Add interfaces, MAC/IP addresses and capability flags
4) Add CSV import/export
5) Build device create/edit/detail APIs
6) Build frontend device table, filters and device detail page
7) Import the audited asset register
Deliverable: Working asset register with exact model, location, role, condition and evidence.
Completion gate: ICT can register, search, edit and export every recovered device; audit trail records changes.
Software Phase 3 — Topology and physical link model
Entry: After inventory.
Developer / implementation steps:
1) Model buildings and network zones
2) Model physical cable/radio/fibre links separately from logical VLAN/routing relationships
3) Link each path endpoint to device/interface IDs
4) Add confidence states: reported, observed, associated, verified
5) Build topology API
6) Build interactive map/graph UI with manual editing
7) Add import/export of topology JSON/CSV
Deliverable: Campus topology view showing known paths, unknowns and dependencies.
Completion gate: ICT can trace an end-to-end building path and identify unverified links without false connections.
Software Phase 4 — Read-only discovery and vendor adapters
Entry: After topology baseline.
Developer / implementation steps:
1) Implement safe subnet allowlists and scan jobs
2) Read local ARP/neighbour and DHCP lease sources where available
3) Add ICMP/TCP reachability checks with rate limits
4) Add SNMP read-only polling for confirmed devices
5) Add Ubiquiti/airOS adapter for inventoried models and firmware
6) Add TP-Link/D-Link/Cisco adapters only for confirmed equipment and supported methods
7) Save raw observations and normalized fields
8) Add capability matrix and adapter tests
Deliverable: Discovery jobs, device identification, read-only health and capability-aware inventory.
Completion gate: No unsupported device is misrepresented; scans are bounded; adapter errors are isolated and logged.
Software Phase 5 — WAN and monitoring
Entry: After read-only integrations.
Developer / implementation steps:
1) Register Starlink A and B as separate WAN circuits
2) Add scheduled ping/DNS/HTTP checks
3) Store speed-test results entered or collected through an approved method
4) Poll gateway/interface counters where supported
5) Add device and link heartbeat
6) Add stale/degraded/unreachable logic
7) Build WAN and campus health dashboards
8) Add alert thresholds and incident acknowledgement
Deliverable: Two-WAN dashboard, device/link health, alerting and incident timeline.
Completion gate: A WAN outage and a building-link outage are distinguishable; dashboard labels data freshness honestly.
Software Phase 6 — Identity and policy model
Entry: After physical access path is known.
Developer / implementation steps:
1) Confirm AP/gateway authentication features from actual models and firmware
2) Decide captive portal, external RADIUS or enterprise Wi-Fi per supported zone
3) Create student/staff/guest/admin accounts and groups
4) Build CSV import and status sync
5) Add policy assignment and expiry
6) Integrate FreeRADIUS only if supported and tested
7) Record enforcement result separately from policy intent
8) Build user/group/policy UI
Deliverable: Identity lifecycle and access policy workflows; pilot authentication.
Completion gate: Disabled users are denied future access; network outage behaviour is documented; no payment workflow remains in core.
Software Phase 7 — Configuration/change management
Entry: Only after read-only stability.
Developer / implementation steps:
1) Select one spare or non-critical device model
2) Implement configuration export/backup adapter
3) Generate proposed configuration diff from a profile
4) Validate model/firmware compatibility
5) Require approval and maintenance window
6) Execute one device at a time
7) Verify connectivity and compare observed state
8) Store before/after snapshots and rollback instructions
9) Expand to other device families only after lab tests
Deliverable: Audited configuration plans and controlled provisioning for specifically supported devices.
Completion gate: No blind mass configuration; every write action has backup, approval, verification and recovery path.
Software Phase 8 — Reporting, resilience and production
Entry: After pilot.
Developer / implementation steps:
1) Add monthly WAN, availability, incidents and access reports
2) Add database and configuration backup schedules
3) Test full restore on a clean host
4) Test API, database, worker and RADIUS failure separately
5) Add operator runbooks
6) Load-test API and worker queue
7) Train ICT operators
8) Tag release and publish deployment/upgrade instructions
Deliverable: Production release, operator handbook, recovery plan, training and acceptance pack.
Completion gate: Restore drill passes; security and acceptance tests pass; ICT can operate without direct database edits.
20.1 Recommended first 30 development days
Week
Developer focus
Demonstrable output
Week 1
Repository audit, run locally, security fixes list, baseline tests, Alembic setup
Verified build, deployment map, backup/restore notes, first CI checks
Week 2
Inventory and location schema/API, CSV import/export, device pages
ICT can register and browse audited devices
Week 3
Buildings/links topology schema/API and topology UI
First as-built campus map with confirmed/unknown link status
Week 4
Read-only discovery job runner, basic probes, first SNMP/vendor adapter on one lab device
Discovery job and truthful device status for a small verified device set


This is a planning sequence, not a promise that every feature will be production-ready in 30 days. Physical audit findings and hardware access determine adapter scope.
20.2 First release scope — keep it deliberately narrow
Release 1 must deliver secure login, device inventory, buildings/locations, manual topology, bounded discovery, Starlink A/B health, basic alerts and audit history.
Release 1 should be read-only toward network equipment. No mass configuration, firmware flashing, factory reset or automatic radio reconfiguration.
Release 2 adds user identity, access policies and a tested authentication integration for the actual AP/gateway models.
Release 3 adds approved configuration management for specifically supported devices and more advanced reporting.
Do not build a custom network operating system. Build the vendor-neutral management and policy layer around the equipment the University already has.
20.3 Developer definition of done
Feature has an agreed requirement and API contract.
Database changes use Alembic migrations and have a rollback/recovery note.
Backend unit/API tests pass; frontend tests pass for critical flows.
Permissions and audit events are implemented for sensitive operations.
Errors and stale data are visible to operators; no fabricated telemetry.
Documentation and example configuration are updated.
Deployment works from a clean checkout using documented commands.
At least one ICT operator has tested the workflow.
21. Deployment, commands and environment specification
The first production deployment should be a single on-premise Linux host or small server, with Docker Compose. The network's forwarding path must not depend on this host being available. A separate recovery/backup target is required.
21.1 Suggested minimum development commands
# Backend (from backend/)
python -m venv .venv
# activate the virtual environment for your OS
pip install -e '.[dev]'
alembic upgrade head
uvicorn app.main:app --reload
pytest -q

# Frontend (from frontend/)
npm ci
npm run dev
npm run lint
npm run typecheck
npm run test
npm run build

# Local services (from repository root)
docker compose up -d postgres
 docker compose ps
 docker compose logs -f api
Exact package scripts and paths must match the implemented repository. These are target development commands, not a claim that the current repository already uses this structure.
21.2 Environment variables
APP_ENV=production
APP_SECRET_KEY=<generated-secret>
DATABASE_URL=<private-postgresql-url>
CORS_ALLOWED_ORIGINS=<approved-dashboard-origins>
JWT_ISSUER=zyranet
JWT_AUDIENCE=zyranet-admin
LOG_LEVEL=INFO
DISCOVERY_ALLOWED_CIDRS=<explicit-campus-subnets>
DISCOVERY_RATE_LIMIT_PER_SECOND=5
SNMP_DEFAULT_VERSION=3
SNMP_CREDENTIAL_REF=<secret-store-reference>
RADIUS_HOST=<internal-radius-host>
RADIUS_SHARED_SECRET=<secret-store-reference>


Secrets must be supplied by a protected environment/secret mechanism, not committed to Git. Discovery CIDRs must be explicit campus-owned ranges approved by ICT. Never allow arbitrary public IP scanning.
21.3 Deployment topology
Internet/WANs ── Edge gateway (independent of Zyranet)
                         │
                  Campus LAN / management segment
                         │
             Linux host: reverse proxy + frontend
                         ├── FastAPI API
                         ├── PostgreSQL (private bind)
                         ├── Discovery/monitor worker
                         └── FreeRADIUS (only if selected)

Backups ── encrypted off-host storage / removable protected copy
22. Software release gates and ownership
Release
Included capability
Who signs off
R0 — Engineering baseline
Repo runs, secrets/auth fixed, migrations, CI and backup restore
Developer + ICT lead
R1 — Network visibility MVP
Inventory, topology, bounded discovery, WAN/device health, incidents
ICT lead
R2 — Access management pilot
User import, groups, guest workflow, tested RADIUS/portal policy
ICT lead + institutional identity owner
R3 — Controlled device operations
Backups, plans, approvals, selected vendor write adapters
ICT lead + network lead
R4 — Production service
Reports, resilience, restore drill, documentation, training and support schedule
Management + ICT lead


The engineering sequence above is the missing software build plan. The field network restoration and software development proceed in parallel, but write-capable device automation must wait until the physical topology and read-only adapters are reliable.
Revision note: This version adds the software technology stack and staged implementation/build plan.
