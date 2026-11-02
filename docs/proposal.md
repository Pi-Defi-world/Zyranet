CAMPUS CONNECTIVITY & ZYRANET
Institutional Project Proposal, Budget Framework & Delivery Plan

Akwa Ibom State University of Education (AUE)
Centre for Educational Technology  |  ICT Infrastructure Unit
Version 2.0 — Working Draft for technical validation and management review
Prepared: 30 October 2026

1. Executive summary
Akwa Ibom State University of Education intends to restore and extend reliable internet connectivity across its campus, serving students, staff, teaching spaces, administration and examination facilities. The project will begin with the University's existing network infrastructure and two Starlink connections currently accessible to the project team.
Rather than replacing all existing equipment, the project will recover and test the legacy network, reconnect serviceable devices, repair cabling and power issues, and introduce a coordinated management platform called Zyranet. Additional purchases will be made only where field evidence shows a specific gap.
General campus internet access will be free to students, staff and approved guests. Zyranet will be provided to the University as an institutional service subscription (TBD), not as a paid internet package for end users.
This proposal is a planning and approval document. Exact quantities, final topology and most equipment/labour prices are subject to the physical audit and dated supplier quotations. No unverified hardware purchase is assumed.
2. Institutional context and objectives
Connect the University's buildings and priority facilities using existing recoverable network equipment.
Provide campus-wide connectivity for a population of approximately 3,000+ students and 400+ staff.
Use the two Starlink connections currently accessible to the project as the initial internet supply.
Give examinations, administration and teaching services appropriate network priority.
Improve network uptime through power assessment, UPS recovery, solar/inverter planning and cable remediation.
Provide ICT with a central view of network devices, buildings, links, service status, incidents and user access through Zyranet.
Keep the project affordable by reusing institutional assets and procuring only against verified requirements.
3. What the project will and will not do
Included in the project
Not assumed / subject to separate approval
Recover and test existing radios, routers, switches, indoor units, dishes and cabling
Wholesale replacement of all old equipment
Reconnect the existing network where devices and links pass tests
Assuming every device is Omada-compatible or supports VLANs
Integrate two accessible Starlink WAN connections
Assuming access to the other Starlink terminals reportedly owned by the school
Assess optional ISP alternatives, including Airtel ODU and institutional fibre/dedicated internet
Treating Airtel ODU or fibre as available before coverage and provider confirmation
Provide Zyranet network operations and access management
Charging students for general campus internet
Assess Hall A coverage and power needs, including solar/inverter expansion
Unmeasured solar or battery quantities and costs
Prioritise exams, administration and teaching networks where equipment supports it
Guaranteeing 10 Mbps to every registered user simultaneously


4. Existing infrastructure and starting point
The University's recovered inventory includes outdoor and indoor units, transmitters, receivers, dishes and control points associated with School of Science, Primary Education, Provost/Masspool, Library, former Directorate of Degree, Student Affairs and Mathematics. The inventory also identifies D-Link indoor units, Ubiquiti receivers/transmitters and TP-Link CPE610/CPE510 equipment. ICT equipment was not fully included and will be added during the audit.
The project will treat the legacy equipment as potentially reusable because it formed part of the former campus network. The team will first document and test it. A device will be proposed for repair or replacement only after the test result establishes a fault or a specific limitation.
5. Proposed solution
5.1 Restore and connect the existing network
Document the ICT/core location and both accessible Starlink connections.
Visit each building, identify all devices and trace how the buildings connect.
Recover configuration backups where possible and label devices and cables.
Test radios, switches, access points, power injectors and cable runs.
Reconnect the existing building links one at a time and verify end-to-end connectivity.
Repair failed terminations and power issues before purchasing replacement equipment.
5.2 Use two Starlink connections initially
The project baseline is two Starlink connections that the team can access. The school reportedly has about five terminals, but the other units are not included in the initial operating plan until access, ownership and subscription details are confirmed. The two available connections will be tested independently and connected through a suitable multi-WAN arrangement where the existing gateway can support it.
A multi-WAN arrangement can share separate user sessions across both connections and provide failover if one connection fails. It does not guarantee that one user will receive the combined speed of both Starlinks.
5.3 Evaluate other internet providers
Option
Current status
Published / indicative cost
Project recommendation
Starlink A and B
Available to project
₦57,000/month each based on current user-reported price; combined ₦114,000/month
Initial WAN supply
Airtel SmartConnect 5G ODU
Suggested option only; coverage not confirmed
Launch reports in Sept. 2025: ₦25,000 entry/device; ₦25,000/month up to 50 Mbps or ₦45,000/month up to 100 Mbps
Optional field test only after confirming campus 4G/5G signal and current terms
Airtel Dedicated Internet
Potential institutional enquiry
Site-specific quotation; published service page describes dedicated symmetric tiers but no public campus price
Request quote and SLA
Local fibre / business ISP
Potential alternative
TBD after serviceability check and formal quotation
Obtain at least two provider proposals


Any alternative provider must be evaluated on actual campus signal or fibre availability, upload/download performance, peak-hour consistency, latency, installation charge, monthly fee, data policy and service-level agreement. The University should not commit to an ISP based only on advertised speed.
5.4 Priority access for essential university functions
Service area
Proposed treatment
Exams complex
Critical priority, restricted access where required and protected capacity during examination periods
Administration buildings
High priority for institutional operations and records
Teaching and laboratories
High priority for teaching platforms and learning resources
General student access
Fair sharing with reasonable per-device limits
Guest access
Restricted internet access, separated from internal systems
Creative Zone
Included in campus connectivity planning; not a paid internet-access tier


6. Zyranet: the University's network operations platform
Zyranet will give the ICT team one operating view of the campus network. It will complement the different manufacturers' equipment rather than require the University to use one vendor.
Zyranet capability
Institutional benefit
Device and asset register
Know what equipment exists, where it is installed and its condition
Campus network map
Understand how buildings and equipment connect
Network monitoring
See WAN, building-link and device availability where supported
Incident and alert management
Identify outages and record how they were resolved
User and access management
Manage approved student, staff, guest and administrator access
Traffic and priority policies
Apply approved service priorities where network equipment supports them
Reports and audit trail
Review uptime, usage, changes and service performance


Zyranet will be funded by the University through a service subscription. The subscription amount is TBD and will be agreed separately. The service schedule should define support hours, maintenance, software updates, monitoring, backups, response targets, reporting and renewal terms.
7. Power, cabling and building readiness
The project will test existing cables before replacing them, re-terminate faulty ends where possible and replace only runs that remain defective. The team will also inspect available UPS units and identify which can be repaired with battery replacement.
Hall A remains part of the campus coverage objective. Its readiness work must include the required building electrical/roof works and an assessment of additional solar panels and inverter battery capacity so that the building and its network equipment can operate for the required duration. Final power quantities will be based on measured load and runtime targets.
8. Delivery phases and indicative schedule
Phase
Main activities
Indicative duration
Deliverable
0. Mobilisation
Approvals, team, access to two Starlinks, outage plan and safety arrangements
1–3 days
Approved scope and work plan
1. Audit and recovery
Inventory, photos, device tests, cable tracing, radio pair mapping, power assessment
1–2 weeks
Verified asset register, as-built map and fault/gap report
2. Network restoration
Restore core, Starlinks, gateway and existing building links one by one
1–2 weeks
Working core and first verified building paths
3. Power and cabling
Cable repair, UPS testing, surge/earthing work and Hall A power design
2–4 weeks; overlaps
Tested cables and approved power remediation
4. Zyranet operations MVP
Inventory, map, monitoring, alerts, audit and WAN status
2–4 weeks; overlaps
ICT operations dashboard
5. Access and pilot
Student/staff/guest policy, authentication integration and controlled pilot
2–3 weeks
Pilot access and policy tests
6. Campus rollout
Extend to verified buildings; prioritise exams/admin/teaching; train ICT
2–4 weeks
Campus rollout and handover
7. Capacity optimisation
Review Starlink measurements; test optional ISP; obtain institutional ISP quotations
After initial operation
Evidence-based ISP and expansion decision


The indicative delivery window is approximately 8–16 weeks after mobilisation, subject to site access, equipment condition, power/electrical works, procurement lead times and the number of links that require repair. The schedule is not a guarantee; each phase closes on evidence and acceptance.
9. Budget framework
The project will use a reuse-first budget. The following costs are separated into known recurring items, measured quantities and quotation-based work. The audit will establish the quantities before the final procurement budget is submitted.
9.1 Known recurring internet cost
Item
Monthly cost
Annual cost
Starlink A
₦57,000
₦684,000
Starlink B
₦57,000
₦684,000
Total for two accessible services
₦114,000
₦1,368,000


9.2 Procurement and project cost schedule
Budget line
Quantity basis
Amount
Network gateway / multi-WAN
Only if existing gateway cannot support two WANs and required policies
TBD
Core / building switches
Only where recovered switches fail verified requirements
TBD
Access points / radio equipment
Only for measured coverage gaps or failed legacy devices
TBD
Cabling, connectors and patching
Measured failed runs and termination requirements
TBD
Cable tester, crimping and installation tools
One supervised field kit plus consumables
TBD
PoE injectors, surge protectors and earthing
Matched to actual devices and exposed links
TBD
UPS batteries / new UPS units
Based on UPS triage and measured critical load
TBD
Hall A solar/inverter/battery expansion
Electrical load and runtime design, then contractor quote
TBD
Other building power remediation
Measured loads and site inspection
TBD
Network engineer and radio technician
Itemised days, work packages, transport and safety equipment
TBD
Cabling technicians
Measured runs, terminations and test certificates
TBD
Electrical/solar contractor
Design, supply, installation, safety and commissioning
TBD
Zyranet software implementation
Repository audit, development, integration, deployment and training
TBD
Zyranet institutional service subscription
Support, updates, monitoring, maintenance and agreed service levels
TBD
ISP alternative / dedicated link
Only after provider coverage check and formal quotation
TBD
Contingency
Management-approved allowance after measured BOQ
TBD


The final budget will be presented as a priced BOQ with quantity, specification, unit cost, total, supplier quotation date and approval status. No replacement device quantity or solar capacity is invented in this draft.
9.3 Cost-control rules
Use existing equipment first where it passes inspection and performance tests.
Obtain dated quotations for all hardware, electrical, solar and contractor work.
Require itemised labour and material costs; avoid a single unexplained installation lump sum.
Purchase only after the technical lead documents the gap and the University approves the request.
Keep the Zyranet service subscription separate from one-time network installation and equipment costs.
10. Project team and professional services
Role
Work to be performed
Fee
Project / network lead
Design oversight, topology, change control, acceptance and handover
TBD
Network engineer
Gateway, routing, WAN failover, IP plan, segmentation, QoS and security
TBD
Wireless / radio technician
Outdoor radio inspection, alignment, configuration recovery and link tests
TBD
Cabling technicians
Cable tracing, re-termination, wire-map testing, labelling and documentation
TBD
Electrical / solar contractor
UPS/inverter/panel/battery sizing, electrical work, earthing and commissioning
TBD
Zyranet developer
Platform audit, software implementation, device integrations, deployment and training
TBD
University ICT operators
Daily operations, user administration, monitoring and first-line response
University assignment


Professional fees will be agreed after the audit defines the number of buildings, links, cable runs, devices and required workdays. The University should request itemised quotations with deliverables, duration, transport, safety arrangements, warranty and payment milestones.
11. Expected deliverables
Verified asset register for recovered network equipment.
Campus physical and logical network map showing confirmed links and unknowns.
Test reports for radios, switches, access points, WAN connections and active cable runs.
Restored network paths for buildings that pass testing.
Approved IP addressing, routing, security and network-priority plan.
Power and UPS assessment, including Hall A solar/inverter requirements.
Zyranet operations platform MVP and institutional service schedule.
Student/staff/guest access pilot and operator procedures.
Final priced bill of quantities based on measured requirements.
Training, configuration backups, maintenance plan and handover report.
12. Risks and safeguards
Risk
Project response
Some old equipment may fail testing
Repair where economical; replace only the affected item/link with management approval
Unknown links or cable routes
Trace and label before reconnecting; maintain an unknowns register
Two Starlinks may not meet all peak demand
Measure actual utilisation; apply fair sharing and priorities; assess further ISP only with evidence
Remote buildings lose power
Include building-level power in the load survey and protect critical network devices
Mixed-vendor equipment has different capabilities
Use vendor-neutral inventory and supported integrations; do not promise universal configuration
Project cost grows through premature procurement
Audit-first procurement and itemised approvals
Zyranet service interruption
Keep network forwarding independent where possible and document emergency operation


13. Management decisions requested
Approve the reuse-first campus connectivity recovery and improvement project.
Authorise the ICT team and appointed technicians to inspect and recover the legacy devices and trace campus links.
Confirm access to the two Starlink terminals and their account/plan details.
Approve a Phase 1 audit and field testing budget (TBD after quotations).
Authorise quotations for network engineering, cabling, electrical/solar work and Zyranet implementation.
Confirm that general campus internet access is free to students, staff and approved guests.
Approve Zyranet as a University-funded service subscription, with the subscription price and service levels to be agreed.
Permit the project team to request optional ISP proposals, without committing the University to Airtel or another provider before testing and approval.
14. Pricing and source notes
Starlink: Starlink Nigeria's public residential page displayed service starting at ₦57,000/month at the time of review. The project budget uses the University's stated current price of ₦57,000 per accessible connection; the actual subscription invoice is authoritative.
Airtel ODU: launch reporting in September 2025 described SmartConnect 5G ODU at ₦25,000 entry price, with ₦25,000/month for up to 50 Mbps or ₦45,000/month for up to 100 Mbps. This is a suggestion only. Campus availability, signal quality, current pricing and terms are unconfirmed.
Airtel dedicated internet: the provider advertises dedicated symmetric internet options but requires a quotation for price and serviceability. Local fibre providers must also be asked for campus-specific quotes.
Starlink Nigeria: https://www.starlink.com/ng/residential
Airtel SmartConnect ODU launch report: https://businessday.ng/technology/article/airtel-nigeria-launches-smartconnect-5g-odu-router-to-expand-broadband-access-nationwide/
Airtel Dedicated Internet: https://www.airtel.com.ng/ng/business/dedicated-internet
NCC approved operator bundle plans: https://ncc.gov.ng/approved-operator-bundle-plans
15. Approval and sign-off
Approver / responsibility
Name / signature
Date
Vice-Chancellor / Management




Centre for Educational Technology




ICT Infrastructure Unit




Project / Network Lead




Procurement / Finance






End of institutional proposal draft. The final financial submission will follow the Phase 1 audit and supplier quotations.
16. Zyranet software development approach
Zyranet will be developed by extending the existing application in stages. The University does not need to purchase a new network operating system. The software will provide a common management interface for the different brands of network equipment already in use.
16.1 Technology foundation
Area
Technology / approach
Purpose
Backend
Python and FastAPI
Build secure application APIs and network integrations
Database
PostgreSQL
Store equipment, buildings, links, users, policies and operational records
Web dashboard
TypeScript and React
Provide the ICT operations interface
Network integrations
Python-based SNMP, API and supported SSH/CLI adapters
Read information from compatible Ubiquiti, TP-Link, D-Link, Cisco and other devices
Authentication
FreeRADIUS where supported by the recovered network equipment
Connect user identity to network access
Deployment
Linux server, Docker Compose and HTTPS reverse proxy
Run the service reliably on the University's infrastructure
Quality assurance
Automated software tests, field device tests and restore drills
Verify that the system works before campus-wide release


The existing Python/FastAPI and PostgreSQL foundation will be retained where it is suitable. The software will be developed incrementally; it will not require all old devices to support one manufacturer's controller.
16.2 Software delivery stages
Stage
What will be built
Completion evidence
1. Codebase audit and security
Review current Zyranet code, deployment and database; correct authentication and security issues
Verified application baseline, backup and secure development setup
2. Device and building registry
Register equipment, models, locations, interfaces and condition
ICT can search and manage the recovered asset register
3. Campus network map
Record buildings, cable/radio links and their verification status
ICT can view known network paths and outstanding unknowns
4. Discovery and monitoring
Find reachable devices and monitor supported device/WAN status
Dashboard shows verified, stale, unknown and unavailable states
5. User and access management
Student/staff/guest accounts and compatible authentication integration
Controlled pilot with account lifecycle tests
6. Configuration and reporting
Approved configuration backups/changes for supported devices; reports and alerts
Audited change records and operational reports
7. Production and handover
Backup/restore, security tests, training, deployment and support documentation
ICT acceptance and production handover


16.3 Development and acceptance method
Audit the current Zyranet repository and preserve the working application and database before making changes.
Build the inventory and building map using information collected by the field engineering team.
Implement read-only discovery and monitoring before allowing software to change device configurations.
Test integrations against actual recovered devices, beginning with one representative device from each confirmed model family.
Introduce student/staff access only after the installed access equipment and authentication method have been tested.
Release each stage only after ICT reviews the working feature and the required tests pass.
The first software release will focus on secure administration, equipment inventory, campus topology, discovery and the health of the two Starlink connections. User access management and controlled device configuration will follow after the physical network is understood.
17. Zyranet service subscription
The University will fund Zyranet through an institutional service subscription (TBD). The service schedule will specify software maintenance, security updates, monitoring support, backups, reporting, support hours, response targets, training and renewal terms. This subscription is separate from internet subscriptions, one-time equipment procurement and contractor installation fees.
Revision note: This version adds the software technology stack and staged implementation/build plan.
