# Zyranet Legacy Network Recovery & Device Provisioning

Technical design specification · Campus networking · Legacy Ubiquiti and mixed-vendor hardware

The missing piece in Zyranet is a device discovery, recovery, and provisioning system that helps the ICT team take old networking equipment from an unknown or incompatible configuration and safely integrate it into the new campus network.

Your Ubiquiti access points and outdoor radios are a good example. A device can be powered on and physically connected yet remain inaccessible because it has an old static IP, the wrong operating mode, a mismatched wireless configuration, an unknown management subnet, outdated firmware, or a damaged configuration.

We should solve that as a first-class part of Zyranet, not as a collection of manual instructions.

My recommendation is to design a new subsystem called Zyranet Device Recovery & Provisioning (ZDRP). It will discover equipment, identify what it can support, help recover management access, prepare a compatible configuration, apply changes through supported methods, and verify that each device works afterward.

There is one important boundary: we should not build a new operating system for every device as the first solution. Many older Ubiquiti airMAX radios, consumer access points, and switches use different chipsets, bootloaders, radio drivers, and proprietary hardware interfaces. A universal replacement firmware would be a major hardware-specific engineering project and could permanently disable equipment if done incorrectly.

Instead, Zyranet should support three levels:

1. Discover and recover: locate the device, identify it, determine its current state, and restore management access.
2. Configure and standardize: apply the safest compatible configuration using the vendor's existing firmware or supported management interfaces.
3. Replace firmware only where justified: support open firmware or a custom operating system for specifically verified hardware models, with tested images and recovery procedures.

This gives you a realistic way to reuse the old equipment while leaving a path to more advanced automation later.

# Part I — System architecture and operating model

## 1. Objectives and scope

ZDRP will be a subsystem inside Zyranet, not a separate operating system or an unrelated product.

Its job is to take network devices through a controlled lifecycle:

- Find devices on known and previously unknown management networks.
- Identify vendor, model, hardware revision, firmware, MAC address, IP address, and available management protocols where discoverable.
- Detect configuration problems such as wrong subnets, duplicate addresses, unreachable gateways, incorrect operating modes, and missing management access.
- Guide an operator through safe recovery.
- Generate a device-specific configuration from an approved campus profile.
- Apply configuration through a supported adapter or provide a guided manual procedure when automation is impossible.
- Verify connectivity, configuration, and reachability after changes.
- Maintain a history of changes and a recovery path for failures.

The system must distinguish between discovering a device, being able to log into it, and being able to configure it. Those are three different capabilities.

## 2. Architecture

\#chatgpt-mermaid-\_r_lb\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_lb\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_lb\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_lb\_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_lb\_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_lb\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_lb\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_lb\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_lb\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_lb\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_lb\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_lb\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_lb\_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_lb\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-\_r_lb\_ p{margin:0;}#chatgpt-mermaid-\_r_lb\_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_lb\_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_lb\_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_lb\_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-\_r_lb\_ .label text,#chatgpt-mermaid-\_r_lb\_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_lb\_ .node rect,#chatgpt-mermaid-\_r_lb\_ .node circle,#chatgpt-mermaid-\_r_lb\_ .node ellipse,#chatgpt-mermaid-\_r_lb\_ .node polygon,#chatgpt-mermaid-\_r_lb\_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_lb\_ .rough-node .label text,#chatgpt-mermaid-\_r_lb\_ .node .label text,#chatgpt-mermaid-\_r_lb\_ .image-shape .label,#chatgpt-mermaid-\_r_lb\_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-\_r_lb\_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-\_r_lb\_ .rough-node .label,#chatgpt-mermaid-\_r_lb\_ .node .label,#chatgpt-mermaid-\_r_lb\_ .image-shape .label,#chatgpt-mermaid-\_r_lb\_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-\_r_lb\_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-\_r_lb\_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_lb\_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_lb\_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-\_r_lb\_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-\_r_lb\_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_lb\_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_lb\_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_lb\_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-\_r_lb\_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-\_r_lb\_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_lb\_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_lb\_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-\_r_lb\_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_lb\_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-\_r_lb\_ .icon-shape,#chatgpt-mermaid-\_r_lb\_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_lb\_ .icon-shape p,#chatgpt-mermaid-\_r_lb\_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-\_r_lb\_ .icon-shape .label rect,#chatgpt-mermaid-\_r_lb\_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_lb\_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-\_r_lb\_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-\_r_lb\_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_lb\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_lb\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_lb\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_lb\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_lb\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_lb\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_lb\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_lb\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_lb\_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-\_r_lb\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_lb\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_lb\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_lb\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_lb\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_lb\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_lb\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_lb\_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_lb\_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_lb\_ .node tspan[font-weight="normal"],#chatgpt-mermaid-\_r_lb\_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-\_r_lb\_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-\_r_lb\_ .node rect,#chatgpt-mermaid-\_r_lb\_ .node circle,#chatgpt-mermaid-\_r_lb\_ .node ellipse,#chatgpt-mermaid-\_r_lb\_ .node polygon,#chatgpt-mermaid-\_r_lb\_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_lb\_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-\_r_lb\_ .mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2,2;}#chatgpt-mermaid-\_r_lb\_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-\_r_lb\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_lb\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}ICT OperatorZyranet Recovery ConsoleRecovery APIDiscovery and ProvisioningWorkerDevice InventoryPostgreSQLDiscovery EngineDevice IdentificationVendor and Protocol AdaptersConfiguration Profile EngineValidation and Diff EngineOperator ApprovalConfiguration BackupPost-Change VerificationLegacy Network DevicesAudit and Job History

### Responsibilities

| Module                     | Responsibility                                                                                    |
| -------------------------- | ------------------------------------------------------------------------------------------------- |
| Recovery Console           | Device list, scan wizard, configuration preview, approvals, recovery instructions                 |
| Discovery Engine           | ARP/neighbour inspection, bounded subnet discovery, ICMP/TCP checks, supported protocol discovery |
| Identification Engine      | Vendor OUI lookup, model detection, firmware and capability inventory                             |
| Adapter Registry           | Defines supported read, configure, backup, and verification operations per device family          |
| Profile Engine             | Converts a desired campus role into a model-compatible configuration                              |
| Diff and Validation Engine | Compares current and proposed state, checks required fields and risky changes                     |
| Provisioning Worker        | Executes approved jobs with timeouts, concurrency limits, and rollback checks                     |
| Recovery Workflow          | Provides local reset, direct Ethernet access, static-IP guidance, and vendor recovery paths       |
| Audit Service              | Records who initiated a change, what was attempted, what changed, and the result                  |

The worker should run with tightly scoped network access on a dedicated management host or management network. The public-facing dashboard should not have unrestricted access to every device on the LAN.

## 3. Device lifecycle and recovery state machine

Every device should have a tracked state. This makes the system usable by an ICT team instead of requiring someone to remember which radios have already been repaired.

\#chatgpt-mermaid-\_r_li\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_li\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_li\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_li\_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_li\_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_li\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_li\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_li\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_li\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_li\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_li\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_li\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_li\_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_li\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-\_r_li\_ p{margin:0;}#chatgpt-mermaid-\_r_li\_ defs [id$="-barbEnd"]{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_li\_ g.stateGroup text{fill:rgb(31, 78, 148);stroke:none;font-size:10px;}#chatgpt-mermaid-\_r_li\_ g.stateGroup text{fill:rgb(237, 237, 237);stroke:none;font-size:10px;}#chatgpt-mermaid-\_r_li\_ g.stateGroup .state-title{font-weight:bolder;fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_li\_ g.stateGroup rect{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_li\_ g.stateGroup line{stroke:rgb(175, 175, 175);stroke-width:1;}#chatgpt-mermaid-\_r_li\_ .transition{stroke:rgb(175, 175, 175);stroke-width:1;fill:none;}#chatgpt-mermaid-\_r_li\_ .stateGroup .composit{fill:transparent;border-bottom:1px;}#chatgpt-mermaid-\_r_li\_ .stateGroup .alt-composit{fill:#e0e0e0;border-bottom:1px;}#chatgpt-mermaid-\_r_li\_ .state-note{stroke:rgb(58, 132, 63);fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_li\_ .state-note text{fill:rgb(237, 237, 237);stroke:none;font-size:10px;}#chatgpt-mermaid-\_r_li\_ .stateLabel .box{stroke:none;stroke-width:0;fill:rgb(9, 23, 44);opacity:0.5;}#chatgpt-mermaid-\_r_li\_ .edgeLabel .label rect{fill:rgb(9, 23, 44);opacity:0.5;}#chatgpt-mermaid-\_r_li\_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_li\_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_li\_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_li\_ .edgeLabel .label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_li\_ .label div .edgeLabel{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_li\_ .stateLabel text{fill:rgb(237, 237, 237);font-size:10px;font-weight:bold;}#chatgpt-mermaid-\_r_li\_ .node circle.state-start{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_li\_ .node .fork-join{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_li\_ .node circle.state-end{fill:rgb(31, 78, 148);stroke:transparent;stroke-width:1.5;}#chatgpt-mermaid-\_r_li\_ .end-state-inner{fill:transparent;stroke-width:1.5;}#chatgpt-mermaid-\_r_li\_ .node rect{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_li\_ .node polygon{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_li\_ [id$="-barbEnd"]{fill:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_li\_ .statediagram-cluster rect{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_li\_ .cluster-label,#chatgpt-mermaid-\_r_li\_ .nodeLabel{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_li\_ .statediagram-cluster rect.outer{rx:5px;ry:5px;}#chatgpt-mermaid-\_r_li\_ .statediagram-state .divider{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_li\_ .statediagram-state .title-state{rx:5px;ry:5px;}#chatgpt-mermaid-\_r_li\_ .statediagram-cluster.statediagram-cluster .inner{fill:transparent;}#chatgpt-mermaid-\_r_li\_ .statediagram-cluster.statediagram-cluster-alt .inner{fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_li\_ .statediagram-cluster .inner{rx:0;ry:0;}#chatgpt-mermaid-\_r_li\_ .statediagram-state rect.basic{rx:5px;ry:5px;}#chatgpt-mermaid-\_r_li\_ .statediagram-state rect.divider{stroke-dasharray:10,10;fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_li\_ .note-edge{stroke-dasharray:5;}#chatgpt-mermaid-\_r_li\_ .statediagram-note rect{fill:rgb(48, 48, 48);stroke:rgb(58, 132, 63);stroke-width:1px;rx:0;ry:0;}#chatgpt-mermaid-\_r_li\_ .statediagram-note rect{fill:rgb(48, 48, 48);stroke:rgb(58, 132, 63);stroke-width:1px;rx:0;ry:0;}#chatgpt-mermaid-\_r_li\_ .statediagram-note text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_li\_ .statediagram-note .nodeLabel{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_li\_ .statediagram .edgeLabel{color:red;}#chatgpt-mermaid-\_r_li\_ [id$="-dependencyStart"],#chatgpt-mermaid-\_r_li\_ [id$="-dependencyEnd"]{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);stroke-width:1;}#chatgpt-mermaid-\_r_li\_ .statediagramTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_li\_ [data-look="neo"].statediagram-cluster rect{fill:rgb(9, 23, 44);stroke:url(#chatgpt-mermaid-\_r_li\_-gradient);stroke-width:1;}#chatgpt-mermaid-\_r_li\_ [data-look="neo"].statediagram-cluster rect.outer{rx:5px;ry:5px;filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_li\_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_li\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_li\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_li\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_li\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_li\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_li\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_li\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_li\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_li\_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-\_r_li\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_li\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_li\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_li\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_li\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_li\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_li\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_li\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}DiscoveredIdentifiedReachableUnreachableReadOnlyAuditRecoveryRequiredManualRecoveryConfigPlannedAwaitingApprovalBackedUpApplyingVerifyingReadyRollbackRequiredDriftDetectedAccess restoredLocal action neededAll checks passVerification failsConfig changed later

### State definitions

- Discovered: an IP or MAC address was observed, but the device type is not yet confirmed.
- Identified: sufficient evidence exists to assign a probable vendor/model and supported capabilities.
- Reachable: at least one management protocol responds.
- Unreachable: the device was previously known or discovered but is not responding from the current probe location.
- Recovery required: the operator must restore addressing or management access.
- Read-only audit: current configuration is collected where the adapter supports it.
- Configuration planned: the desired role and proposed changes have been generated.
- Awaiting approval: a human reviews the proposed changes and impact.
- Backed up: a supported configuration backup or documented recovery snapshot exists.
- Applying: the approved changes are being applied.
- Verifying: connectivity and configuration are checked.
- Ready: required checks pass and the device has been assigned to its intended role.
- Drift detected: the observed state differs from the last approved state.

Not every device can support every state. An unmanaged switch, for example, may only be inventoried and tested at the link level. The UI must not show it as fully provisioned.

# Part II — Discovery and recovery engine

## 4. Discovery strategy

The existing Zyranet scanner already uses ARP/neighbour information, active probes, and MAC vendor identification. That is useful, but it is not sufficient for recovering devices whose management IP is unknown or lies outside the server's subnet.

Source: [existing discovery scanner](https://github.com/Pi-Defi-world/Zyranet/blob/main/app/services/scanner.py?utm_source=chatgpt.com).

The new discovery system should use multiple methods, in increasing order of intrusiveness.

### 1

Passive discovery

Read local neighbour tables, DHCP leases where available, switch forwarding tables through supported SNMP, and existing inventory records. This is the safest starting point.

### 2

Bounded active discovery

Probe only explicitly approved subnets and IP ranges. Use rate-limited ICMP and TCP connection checks, plus HTTP/HTTPS service detection on known management ports.

### 3

Protocol and model discovery

Query supported SNMP endpoints, known vendor APIs, and device management pages. Extract model or firmware information only when the protocol provides reliable evidence.

### 4

Guided local recovery

If the device is not reachable, provide an operator workflow for direct Ethernet connection, static addressing, identification labels, reset procedures, and vendor-specific recovery.

### Why subnet discovery alone fails

Suppose a radio has a static management address of `192.168.1.20`, but the new network uses `10.20.0.0/24`.

A scanner operating only on the new subnet will not reliably discover or reach that radio. A router does not automatically expose devices from every old subnet, and a host's ARP table only contains devices it has recently learned about on its local network.

The recovery system therefore needs an isolated recovery interface or a dedicated recovery laptop that can be placed temporarily on the old management subnet.

For legacy equipment, this is often the most reliable recovery method.

## 5. Recovery workstation design

I recommend providing a dedicated recovery mode on the Zyranet management host or a technician's laptop.

The recovery workstation should have:

- A wired Ethernet interface.
- A supported USB-to-Ethernet adapter as a backup.
- A way to assign a temporary static IP address.
- A local inventory of approved vendor documentation and firmware files.
- A browser and supported command-line networking tools.
- A known-good cable and a means of checking link state.
- A safe method to back up configuration files where supported.

The initial implementation should use the existing Linux host or a normal technician laptop. It does not need a custom Linux distribution.

### Recovery procedure for an unreachable Ubiquiti device

Step 1 — Isolate and identify

Record the device model, MAC address, label, power source, port connections, and current physical role. Disconnect it from the production network if necessary to avoid duplicate IPs or accidental DHCP conflicts.

Step 2 — Check physical and link state

Verify power, Ethernet link, PoE compatibility, cable integrity, and the device's status LEDs. A failed power source or incompatible PoE injector can look like a software problem.

Step 3 — Discover the management address

Check the old router's DHCP leases, ARP tables, known device labels, and the existing network configuration. If needed, connect directly and use a bounded discovery scan on a technician-controlled recovery subnet.

Step 4 — Access the management interface

Assign the laptop a compatible temporary address if the device uses a known static subnet. Use the correct vendor documentation for the exact model and firmware. Do not assume the default address or credentials are still valid.

Step 5 — Back up and inspect

Record firmware version, operating mode, management IP, subnet, gateway, wireless mode, SSID, channel, security, and any bridge/routing settings. Export the configuration if supported.

Step 6 — Configure the intended role

Apply a reviewed configuration that matches the device's purpose: point-to-point bridge, point-to-multipoint base, station, or client-facing access point. Change management addressing and security settings only after confirming the intended network.

Step 7 — Verify and reattach

Confirm management reachability from the new management subnet, correct bridge/routing behaviour, connectivity through the intended link, and absence of DHCP or IP conflicts before reconnecting the device to production.

Important: Ubiquiti's airMAX NanoStation M2 is not the same device family as every Ubiquiti UniFi access point. The recovery interface, firmware, management protocol, and supported configuration method differ. ZDRP must identify the exact model before presenting instructions.

## 6. Device identification and capability registry

Zyranet should not identify devices by vendor name alone. The MAC address OUI can suggest a manufacturer, but it cannot reliably establish the exact model, firmware, or configuration capabilities.

Each discovered device should have a confidence-rated identity record.

| Field               | Example                        | Evidence                                       |
| ------------------- | ------------------------------ | ---------------------------------------------- |
| Vendor              | Ubiquiti Networks              | MAC OUI or management response                 |
| Product family      | airMAX                         | Model or firmware metadata                     |
| Model               | NanoStation M2                 | Device-reported model or physical label        |
| Hardware revision   | Device-reported revision       | Management interface or label                  |
| Firmware            | airOS version                  | Device-reported firmware                       |
| Management IP       | `192.168.1.20`                 | Verified response or operator confirmation     |
| MAC address         | Device's hardware address      | Neighbour table or device interface            |
| Role                | PtMP station                   | Current configuration or operator confirmation |
| Management protocol | HTTPS, SSH, SNMP               | Verified service availability                  |
| Capability profile  | Bridge mode supported          | Model-specific adapter definition              |
| Confidence          | Confirmed / probable / unknown | Strength of evidence                           |

### Capability-based adapters

Instead of writing one large collection of vendor-specific conditionals, define an adapter contract.

```
class DeviceAdapter:    async def identify(self, target): ...    async def inspect(self, device): ...    async def get_capabilities(self, device): ...    async def export_config(self, device): ...    async def validate_config(self, device, config): ...    async def apply_config(self, device, config): ...    async def verify(self, device, expected_state): ...
```

This is an architectural interface, not an implemented adapter.

Each method should explicitly report whether it is supported for a particular device and firmware version. An adapter must not pretend to support configuration export or rollback when the underlying hardware does not provide it.

### Initial adapter priorities

[Point d'accès Wi-Fi PoE pour extérieur Ubiquiti Networks NanoStation M2 150 MBit/s 2.4 GHz - Cdiscount Informatique](https://images.openai.com/static-rsc-4/X4XbF7mYxZJvO-SC7aV8V3IPcn59gdiGq4hPLQEB9Ft9RnNMht-WU5yc8AKUIWzJRkno-JmIonRLDauieFw4ovC-TqQCEFldPuPdaRad0xCrE326WnOEw2YZDqH5c-FxgsakRrcf9oI4lFh-lLcq3zCo6x7kBX6UfugWF6-oqmo?purpose=inline)

1\. Ubiquiti airMAX / airOS

Highest priority because your existing outdoor radios and connectivity problems make this the most immediately useful family.

Start with identification, read-only inspection where supported, management IP recovery, bridge/role configuration guidance, and verification.

[TP-LINK TL-WR740N Wireless Router 802.11b/g/n up to 150Mbps/ 10/100 Mbps Ethernet Port x4 - Newegg.com](https://images.openai.com/static-rsc-4/mRSwIKEYFKXlpPCUBzh95k7F5yqNtHbMQ5QkIKBDHayl_ZLhegSs8_Fmccj6bQOfP9z9DmEkiHiLB9_aAakpJbGL3oMxI1ELT2mowdZjZ2XXOFyJStfL28v0J7sq1r5nrB2IeQ4QfPV2058KtUMuh36SwFblSRkDu044v2dgyCY?purpose=inline)

2\. TP-Link routers and access points

Focus on distinguishing router mode from access-point mode, disabling conflicting DHCP/NAT where appropriate, setting management addresses, and validating connectivity.

[10 Port Ethernet Switch | 10 Port Gigabit Ethernet Switch](https://images.openai.com/static-rsc-4/UM5Fniwscx-2NU048J4tAeAG0HDNoJK31osODkKvDedPS6S5PkerwEfnn0oYyJwwqbFb8UsoJYtcvNCHk7k4CGo4ltxD2cDyxQKXIaxfytVPNXCK3P-QXfKt1uQb2Kz95xh179nVK-GmD79t8pjhg37FE3hMNpDRnQyBzL9JpN4?purpose=inline)

3\. Managed switches

Use SNMP and supported vendor APIs for identification, interface state, link metrics, and topology discovery. Unmanaged switches will remain passive inventory items.

[Ubiquiti UAP-AC-PRO wireless access point 1300 Mbit/s White Power over Ethernet (PoE) - Globe Systems A/S](https://images.openai.com/static-rsc-4/d2Qln_BIHHWOPP55fhkn3NehEUgtoHR_844k37ZaDBOL2UgRIAvtoN46NI9UYCkrsHY9dnUrE2xXqzn5yqZb7q-qFqFBiuAjjmIsujjg2SrW-sWMGQWAn4Nyc1oWUYjFWzCafOnoIG4BaMgYGKIsaAS-iIrGgkin0DLNXK5sHcw?purpose=inline)

4\. Other access points

Add adapters after model inventory. Prioritize models with documented management interfaces and a viable firmware support path.

The first production milestone should not be “support all networking hardware.” It should be “reliably recover and configure the verified models that the school actually owns.”

# Part III — Configuration profiles and safe provisioning

## 7. Desired-state configuration profiles

A device's configuration should be generated from its intended role and the school's network policy, not copied blindly from another device.

ZDRP should provide a small set of role templates.

Wireless backhaul base

Defines the compatible wireless mode, link security, channel plan, management address, bridge behaviour, and allowed management access for a base radio.

Remote bridge / station

Matches the intended base network, uses compatible radio settings, maintains the correct bridge behaviour, and assigns a unique management address.

Client-facing access point

Defines the supported SSID and security mode, channel and radio settings, management addressing, and bridge/AP mode appropriate to the device.

Edge router

Defines routing, DHCP, NAT, firewall, and VLAN behaviour only where the hardware supports the required functions and the device is explicitly designated to perform them.

### Example desired-state profile

This example describes the logical intent for a remote building bridge. It is not a firmware-specific configuration file, and ZDRP must translate it through a verified adapter before applying it.

```
profile:
  id: campus-building-bridge
  version: 1

  device:
    family: ubiquiti-airmax
    role: station-bridge

  management:
    addressing: static
    address: "<assigned-unique-management-ip>"
    gateway: "<management-gateway>"
    allow_management_from:
      - "<ict-management-subnet>"

  network:
    mode: transparent_bridge
    dhcp_server: false
    nat: false

  wireless:
    peer: "<approved-base-radio>"
    security_profile: campus-backhaul
    channel_plan: approved-backhaul-plan

  verification:
    management_reachable: true
    bridge_path_reachable: true
    unexpected_dhcp_server: false
```

A profile contains references to approved secrets and network allocations; it should not contain actual shared passwords or credentials in the repository.

### Configuration compiler

The profile engine should perform five stages:

1. Validate the requested role against the identified device's capabilities.
2. Resolve the management IP, gateway, subnet, SSID, channel, and security profile.
3. Produce a device-specific configuration or guided manual instructions.
4. Generate a diff between current and intended state.
5. Reject unsupported or unsafe changes before the operator approves the job.

If a model cannot support a requested capability, the compiler should return a clear error rather than silently omitting the requirement.

## 8. Configuration safety and recovery

Changing the management IP can disconnect the operator. Changing wireless security or channel settings can break a building link. Changing bridge mode can introduce a loop or interrupt traffic.

For that reason, provisioning needs an explicit safety model.

### Required safety controls

- Read the current state before modifying the device, wherever supported.
- Back up the existing configuration and securely store the backup.
- Require a human to approve changes that affect addressing, management access, radio links, DHCP, routing, or firmware.
- Apply changes to one device at a time when it is part of a live backhaul path.
- Provide an out-of-band or direct-cable recovery route when possible.
- Use bounded connection timeouts and a job lock to prevent concurrent changes to the same device.
- Verify that the new management address is reachable from the intended subnet.
- Test the actual building link before declaring the device ready.
- Stop the rollout if verification fails.
- Record whether rollback is supported, attempted, or requires manual intervention.

Do not promise automatic rollback on every old device. Some web interfaces cannot export configuration, some changes require a reboot, and some devices cannot restore a configuration after a failed address change. Those devices must use a supervised recovery procedure instead.

### Example provisioning job

\#chatgpt-mermaid-\_r_pj\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_pj\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_pj\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_pj\_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_pj\_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_pj\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_pj\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_pj\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_pj\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_pj\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_pj\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_pj\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_pj\_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_pj\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-\_r_pj\_ p{margin:0;}#chatgpt-mermaid-\_r_pj\_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_pj\_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_pj\_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_pj\_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-\_r_pj\_ .label text,#chatgpt-mermaid-\_r_pj\_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_pj\_ .node rect,#chatgpt-mermaid-\_r_pj\_ .node circle,#chatgpt-mermaid-\_r_pj\_ .node ellipse,#chatgpt-mermaid-\_r_pj\_ .node polygon,#chatgpt-mermaid-\_r_pj\_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_pj\_ .rough-node .label text,#chatgpt-mermaid-\_r_pj\_ .node .label text,#chatgpt-mermaid-\_r_pj\_ .image-shape .label,#chatgpt-mermaid-\_r_pj\_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-\_r_pj\_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-\_r_pj\_ .rough-node .label,#chatgpt-mermaid-\_r_pj\_ .node .label,#chatgpt-mermaid-\_r_pj\_ .image-shape .label,#chatgpt-mermaid-\_r_pj\_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-\_r_pj\_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-\_r_pj\_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_pj\_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_pj\_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-\_r_pj\_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-\_r_pj\_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_pj\_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_pj\_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_pj\_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-\_r_pj\_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-\_r_pj\_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_pj\_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_pj\_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-\_r_pj\_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_pj\_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-\_r_pj\_ .icon-shape,#chatgpt-mermaid-\_r_pj\_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_pj\_ .icon-shape p,#chatgpt-mermaid-\_r_pj\_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-\_r_pj\_ .icon-shape .label rect,#chatgpt-mermaid-\_r_pj\_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_pj\_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-\_r_pj\_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-\_r_pj\_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_pj\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_pj\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_pj\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_pj\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_pj\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_pj\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_pj\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_pj\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_pj\_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-\_r_pj\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_pj\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_pj\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_pj\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_pj\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_pj\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_pj\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_pj\_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_pj\_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_pj\_ .node tspan[font-weight="normal"],#chatgpt-mermaid-\_r_pj\_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-\_r_pj\_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-\_r_pj\_ .node rect,#chatgpt-mermaid-\_r_pj\_ .node circle,#chatgpt-mermaid-\_r_pj\_ .node ellipse,#chatgpt-mermaid-\_r_pj\_ .node polygon,#chatgpt-mermaid-\_r_pj\_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_pj\_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-\_r_pj\_ .mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2,2;}#chatgpt-mermaid-\_r_pj\_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-\_r_pj\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_pj\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}Select identified deviceSelect role profileValidate model and capabilitiesRead current configurationGenerate configuration diffOperator approves?Abort with no changesSave backup or recoverysnapshotApply configurationReconnect to newmanagement addressVerify management and datapathChecks pass?Mark device readyStop rollout and open recoverycaseNoYesYesNo

## 9. Preventing loops and addressing conflicts

Legacy network migrations frequently fail because several devices are left in router mode or multiple DHCP servers are active.

ZDRP should include preflight checks for:

- Duplicate management IP addresses.
- Multiple unexpected DHCP servers.
- Unexpected NAT or routing on bridge devices.
- Incorrect default gateways.
- Wireless base/station mismatches.
- SSID or security-profile mismatches.
- Incorrect bridge port membership.
- Incompatible channel or wireless mode settings.
- Potential Ethernet loops or multiple paths between switches.

These checks should distinguish between a confirmed issue and a possible risk. For example, two devices responding at the same IP is evidence of a conflict, but a simple scan cannot always determine which device is misconfigured.

# Part IV — Firmware and operating-system strategy

## 10. Should we create a new operating system?

Potentially, for selected hardware. But it should be a separate, carefully scoped research and engineering track.

There are three options.

| Strategy                           | Benefits                                                                       | Risks and limitations                                                                          |
| ---------------------------------- | ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| Existing vendor firmware           | Lowest risk; retains supported radio drivers and hardware behaviour            | Different interfaces, capabilities, and firmware versions                                      |
| Supported open firmware            | Greater automation and potentially consistent configuration on verified models | Hardware support varies; flashing may be irreversible without recovery access                  |
| Custom firmware / operating system | Maximum control over supported devices and integration                         | Requires model-specific bootloader, driver, radio, upgrade, recovery, and security engineering |

For older Ubiquiti devices, the first question is not whether we can build a custom operating system. It is whether the exact hardware revision has a supported and safe upgrade or recovery path.

Some devices have hardware-specific boot processes, proprietary radio components, and limited flash or RAM. An image that works on one revision may not work on another.

### Recommended approach

Phase A — Vendor-firmware automation. Build the discovery engine, profiles, supported adapters, and guided recovery first.

Phase B — Open-firmware evaluation. Identify a small number of verified device models that have mature support in an established open firmware project. Test on spare units in a lab.

Phase C — Controlled firmware management. If the school has enough identical supported hardware, develop a signed firmware catalogue, compatibility checks, staged upgrades, and recovery testing.

Phase D — Custom operating system only if justified. Consider this only if there is a concrete capability that existing firmware cannot provide and the engineering and hardware-maintenance cost makes sense.

The custom firmware must not be treated as a way to force every old AP and outdoor radio into identical software. A better design is one consistent Zyranet management interface with multiple model-specific backends.

### Firmware security requirements

Any future firmware workflow must include:

- Exact model and hardware-revision verification.
- Verified firmware origin and integrity.
- Compatibility checks before flashing.
- Configuration and recovery backups.
- Power-loss and interrupted-upgrade testing.
- Staged rollout and explicit operator approval.
- A documented recovery method for each supported model.
- Secure boot or signed-update verification where the hardware supports it.
- A way to stop distributing a faulty image.

Never flash a firmware image simply because it mentions the same brand or product family.

# Part V — API, database, and implementation design

## 11. Proposed API surface

All recovery and configuration endpoints should require authenticated ICT access. Read-only discovery and write operations should have separate permissions.

Base prefix: `/api/recovery`

| Method | Endpoint                            | Purpose                                               |
| ------ | ----------------------------------- | ----------------------------------------------------- |
| `POST` | `/scans`                            | Start a bounded, approved discovery job               |
| `GET`  | `/scans/{scan_id}`                  | Read scan status and results                          |
| `GET`  | `/devices`                          | Search identified and unidentified devices            |
| `GET`  | `/devices/{device_id}`              | Inspect identity, capabilities, location, and history |
| `POST` | `/devices/{device_id}/inspect`      | Run supported read-only inspection                    |
| `GET`  | `/devices/{device_id}/capabilities` | Return supported operations and limitations           |
| `POST` | `/recovery-sessions`                | Create a guided recovery case                         |
| `GET`  | `/recovery-sessions/{id}`           | Track recovery instructions and progress              |
| `GET`  | `/profiles`                         | List approved configuration profiles                  |
| `POST` | `/plans`                            | Generate a proposed configuration plan                |
| `GET`  | `/plans/{id}`                       | Inspect a plan and its configuration diff             |
| `POST` | `/plans/{id}/approve`               | Approve an authorized configuration plan              |
| `POST` | `/jobs`                             | Execute an approved provisioning job                  |
| `GET`  | `/jobs/{job_id}`                    | Track execution and verification                      |
| `POST` | `/jobs/{job_id}/cancel`             | Cancel a job where safe and supported                 |
| `POST` | `/devices/{device_id}/verify`       | Run approved post-configuration checks                |
| `GET`  | `/devices/{device_id}/history`      | Review prior changes and recovery attempts            |
| `GET`  | `/firmware/catalog`                 | List approved firmware metadata                       |
| `POST` | `/firmware/compatibility-check`     | Check an image against a verified model/revision      |

A firmware upload or flash operation should be a later, separately permissioned feature—not an unrestricted endpoint in the first release.

### Example discovery request

```
{
  "scope": {
    "cidrs": ["192.168.1.0/24"],
    "interfaces": ["recovery0"]
  },
  "methods": [
    "neighbour_table",
    "icmp",
    "http_probe",
    "https_probe"
  ],
  "profile": "legacy-network-recovery",
  "mode": "read_only",
  "rate_limit_per_second": 10
}
```

The server must validate the target range against a configured allowlist and ensure the selected interface exists. A client must not be able to submit arbitrary internet-wide targets or use discovery as a general scanning service.

### Example job status

```
{
  "job_id": "job-example",
  "device_id": "device-example",
  "state": "awaiting_approval",
  "profile": "campus-building-bridge",
  "backup_status": "not_started",
  "verification_status": "not_started",
  "requires_manual_recovery": false,
  "created_by": "ict-operator",
  "created_at": "2026-10-29T10:00:00Z"
}
```

These are proposed API contracts, not endpoints that currently exist in the repository.

## 12. Database schema additions

The existing `devices` and `device_sightings` tables are a starting point. I would add normalized tables rather than storing the entire recovery lifecycle inside a single JSON topology document.

| Table                     | Purpose                                     | Key fields                                        |
| ------------------------- | ------------------------------------------- | ------------------------------------------------- |
| `device_models`           | Known hardware and firmware families        | vendor, model, revision, support status           |
| `device_capabilities`     | Operations supported by each model/firmware | capability, adapter version, support level        |
| `device_interfaces`       | Physical and logical interfaces             | device ID, interface name, MAC, link state        |
| `device_addresses`        | Management and observed IP addresses        | device ID, address, subnet, source, validity      |
| `network_locations`       | Campus, building, floor, room               | parent location, label, location type             |
| `device_config_snapshots` | Encrypted configuration backups or metadata | device ID, storage reference, checksum, timestamp |
| `device_profiles`         | Versioned desired-state profiles            | role, version, profile definition, status         |
| `provisioning_plans`      | Proposed changes and diffs                  | device ID, profile version, risk, approval state  |
| `provisioning_jobs`       | Executions and verification results         | plan ID, status, start/end, result                |
| `recovery_cases`          | Manual recovery workflow                    | device ID, issue, steps, resolution               |
| `discovery_jobs`          | Scan scope and progress                     | allowed targets, methods, timestamps              |
| `discovery_observations`  | Individual discovery findings               | job ID, address, protocol, evidence               |
| `device_audit_events`     | Immutable-style audit history               | actor, action, device, outcome, timestamp         |

“Immutable-style” means the application should be append-only for audit records and tightly restrict updates/deletes; a database administrator can still alter ordinary database tables unless stronger tamper-evidence controls are introduced.

### Data model rules

- A MAC address is not a permanent identity for every possible device interface. Store interface-level MACs as well as the overall device record.
- IP addresses may change. Preserve address history and distinguish configured addresses from observed addresses.
- Device identity must include hardware revision when that affects firmware compatibility.
- Configuration snapshots should be encrypted and access-controlled because they may contain credentials or other secrets.
- Profile and adapter versions must be recorded for every provisioning job.
- Discovery observations should retain evidence and confidence, not just a guessed device type.
- Every change job should link the initiating user, approved plan, backup reference, execution result, and verification result.

### Profile validation

A profile should have a machine-readable schema and version. It should be validated before a job can be approved.

For example, a `station-bridge` profile should be rejected if the identified model does not support the required wireless mode, if the management IP conflicts with an existing allocation, or if the requested security mode is incompatible with the intended base station.

# Part VI — Security review and production requirements

## 13. Immediate security issues to fix

While reviewing the existing Zyranet code, I found a specific issue in `app/security.py` that should be fixed before the recovery subsystem is introduced.

The current `check_login()` function contains this condition:

```
if s.admin_password in password:    return True
```

This checks whether the configured password is a substring of the submitted password. If the configured value is `school-secret`, a submitted value containing `school-secret` plus extra characters can pass this condition. The check should instead use exact plaintext equality when explicitly supporting plaintext configuration, or—preferably—verify against a password hash using a proper password verification function.

There is also a separate concern: the current authentication implementation uses a single configured administrator account and issues JWTs with a 12-hour default lifetime. Before a school deployment, we need account-level permissions, token revocation strategy, shorter configurable sessions where appropriate, login throttling, and MFA for privileged operators.

Source: [current security implementation](https://github.com/Pi-Defi-world/Zyranet/blob/main/app/security.py?utm_source=chatgpt.com).

### Additional controls for device management

- Never store device passwords, SNMP community strings, SSH keys, or Wi-Fi secrets in plaintext configuration files or job logs.
- Avoid trying lists of default credentials or performing password guessing.
- Require explicit authorization before inspecting or changing devices.
- Restrict recovery scans to the school's approved address ranges and interfaces.
- Require operator confirmation before disruptive changes.
- Log configuration changes and administrative actions without logging secret values.
- Separate discovery privileges from configuration privileges.
- Protect backup files and firmware images from unauthorized modification.
- Restrict management interfaces to the ICT management network.
- Ensure a compromised dashboard cannot silently push arbitrary commands to every device.

ZDRP must never automatically reset or reflash a device merely because it is unreachable. Unreachable equipment may be serving an important building link; automatic destructive recovery could disconnect the entire campus.

# Part VII — Deployment and testing

## 14. Recommended deployment layout

For the first release, run Zyranet on a stable Ubuntu Server host with PostgreSQL and a dedicated recovery worker.

\#chatgpt-mermaid-\_r_qe\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_qe\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_qe\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_qe\_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_qe\_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_qe\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_qe\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_qe\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_qe\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_qe\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_qe\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_qe\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_qe\_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_qe\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-\_r_qe\_ p{margin:0;}#chatgpt-mermaid-\_r_qe\_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_qe\_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_qe\_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_qe\_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-\_r_qe\_ .label text,#chatgpt-mermaid-\_r_qe\_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_qe\_ .node rect,#chatgpt-mermaid-\_r_qe\_ .node circle,#chatgpt-mermaid-\_r_qe\_ .node ellipse,#chatgpt-mermaid-\_r_qe\_ .node polygon,#chatgpt-mermaid-\_r_qe\_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_qe\_ .rough-node .label text,#chatgpt-mermaid-\_r_qe\_ .node .label text,#chatgpt-mermaid-\_r_qe\_ .image-shape .label,#chatgpt-mermaid-\_r_qe\_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-\_r_qe\_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-\_r_qe\_ .rough-node .label,#chatgpt-mermaid-\_r_qe\_ .node .label,#chatgpt-mermaid-\_r_qe\_ .image-shape .label,#chatgpt-mermaid-\_r_qe\_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-\_r_qe\_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-\_r_qe\_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_qe\_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_qe\_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-\_r_qe\_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-\_r_qe\_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_qe\_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_qe\_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_qe\_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-\_r_qe\_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-\_r_qe\_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_qe\_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_qe\_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-\_r_qe\_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_qe\_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-\_r_qe\_ .icon-shape,#chatgpt-mermaid-\_r_qe\_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_qe\_ .icon-shape p,#chatgpt-mermaid-\_r_qe\_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-\_r_qe\_ .icon-shape .label rect,#chatgpt-mermaid-\_r_qe\_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_qe\_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-\_r_qe\_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-\_r_qe\_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_qe\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_qe\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_qe\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_qe\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_qe\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_qe\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_qe\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_qe\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_qe\_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-\_r_qe\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_qe\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_qe\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_qe\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_qe\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_qe\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_qe\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_qe\_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_qe\_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_qe\_ .node tspan[font-weight="normal"],#chatgpt-mermaid-\_r_qe\_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-\_r_qe\_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-\_r_qe\_ .node rect,#chatgpt-mermaid-\_r_qe\_ .node circle,#chatgpt-mermaid-\_r_qe\_ .node ellipse,#chatgpt-mermaid-\_r_qe\_ .node polygon,#chatgpt-mermaid-\_r_qe\_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_qe\_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-\_r_qe\_ .mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2,2;}#chatgpt-mermaid-\_r_qe\_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-\_r_qe\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_qe\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}ICT Admin BrowserHTTPS Reverse ProxyZyranet FastAPIPostgreSQLRecovery WorkerEncrypted Backup andFirmware StoreIsolated Management NetworkDedicated Recovery PortOld APs, Radios, Routers andSwitches

### Deployment requirements

- Keep the dashboard and database on the trusted server side.
- Use a dedicated management interface or VLAN for device access.
- Use a separate recovery interface for devices that cannot be reached through the normal management network.
- Do not bridge the recovery interface directly into the production network without an explicit design and firewall policy.
- Keep the provisioning worker's privileges separate from the public web process.
- Encrypt backups and restrict access to firmware and configuration archives.
- Log job status and failures so an interrupted recovery can be resumed safely.

A second physical network interface is useful for recovery, but not mandatory if an equivalent isolated VLAN or a technician-operated laptop provides the same separation.

## 15. Testing strategy

We should validate ZDRP in a lab before using it on a live campus link.

Unit tests

Validate subnet calculations, address conflict detection, model matching, profile schemas, adapter capability checks, configuration diffs, and job state transitions.

Discovery tests

Test devices on the expected subnet, devices with static addresses on an old subnet, devices that do not answer ICMP, duplicate IPs, and devices that are offline.

Security tests

Verify that unauthorized users cannot start scans, read credentials, approve jobs, change device configurations, or upload firmware.

Recovery tests

Test failed logins, unreachable management IPs, interrupted jobs, failed reboots, lost connectivity, configuration restoration, and manual recovery instructions.

End-to-end tests

Configure a spare radio, connect it to a compatible base, verify the bridge path, confirm the management IP is reachable from the intended subnet, and verify client connectivity.

### Initial acceptance criteria

The first release should be considered usable only when it can:

1. Discover and inventory the verified device models in your possession.
2. Detect devices with unknown management addresses through a safe, bounded recovery workflow.
3. Clearly identify which devices can be automatically configured and which require manual intervention.
4. Generate a model-compatible configuration preview before applying changes.
5. Record backups or explicitly identify devices for which backups are unsupported.
6. Execute an approved change on a test device and verify the result.
7. Record failure and recovery instructions without claiming success when verification fails.
8. Protect administrative credentials, device secrets, and configuration backups.
9. Avoid disrupting unrelated devices during a scan or provisioning job.

## 16. Implementation roadmap

| Phase                          | Main deliverable                                                                | Priority |
| ------------------------------ | ------------------------------------------------------------------------------- | -------- |
| 1. Security and inventory      | Fix authentication, inventory actual models, define recovery interfaces         | Critical |
| 2. Discovery engine            | Safe subnet scans, device identity evidence, recovery cases                     | Critical |
| 3. Ubiquiti adapter            | Verified identification and configuration support for your actual airMAX models | Critical |
| 4. Profile engine              | Bridge, station, AP, and management-address profiles with diff validation       | High     |
| 5. Provisioning jobs           | Approval, backup, apply, verify, audit, and failure handling                    | High     |
| 6. TP-Link and switch adapters | Extend support to verified routers and managed switches                         | High     |
| 7. Firmware evaluation         | Lab-test supported open firmware on selected hardware revisions                 | Later    |
| 8. Custom OS research          | Build only if existing firmware cannot meet a proven requirement                | Optional |

The exact firmware and configuration capabilities should be established during Phase 1 rather than assumed in advance.

## 17. What I recommend doing first with your actual equipment

The most useful next step is to recover one representative Ubiquiti device, document its exact model and firmware, and use it as the first supported ZDRP device.

Please gather the following for one of the APs or outdoor radios that you could not reconnect:

- The exact model printed on its label, including hardware revision if shown.
- A photo of its ports and power/PoE injector, if available.
- Whether it powers on and whether its Ethernet link light comes on.
- The old management IP or subnet, if known.
- Whether it was previously a base station, station/receiver, or client-facing AP.
- Whether you can connect a laptop directly to it by Ethernet.

Do not factory-reset the first device yet if it might be one of the radios providing connectivity to another building.

With that information, we can design the first real device adapter against the hardware you own rather than building a generic system that looks complete but cannot safely configure your equipment.

Final architectural decision: Zyranet should become the unified management layer, with a controlled discovery and provisioning engine—not a replacement operating system for every network device. That is the path that gives you the broadest practical compatibility, the lowest initial cost, and a realistic way to recover, standardize, and expand the campus network.