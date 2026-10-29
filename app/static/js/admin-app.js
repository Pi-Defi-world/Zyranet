/** Zyranet NOC dashboard + Packet-Tracer map orchestration. */
(function () {
  const API = "/api";
  const token = () => localStorage.getItem("zyranet_token");

  const PAGES = {
    overview: { title: "Overview", el: "page-overview" },
    network: { title: "Network map", el: "page-network" },
    devices: { title: "Devices", el: "page-devices" },
    sessions: { title: "Live sessions", el: "page-sessions" },
    vouchers: { title: "Vouchers", el: "page-vouchers" },
  };
  const ZONE_META = [
    ["internet", "Internet", "#94a3b8"], ["core", "Core", "#3b82f6"],
    ["admin", "Admin", "#a78bfa"], ["guest", "Guest", "#22c55e"],
    ["bldg-a", "Bldg A", "#fbbf24"], ["bldg-b", "Bldg B", "#fb923c"], ["bldg-c", "Bldg C", "#f472b6"],
  ];
  const activeZones = new Set();

  let mapRefreshTimer = null;

  function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
  function fmtDate(v) { return v ? new Date(v).toLocaleString() : "—"; }
  function ngn(kobo) { return "₦" + (Number(kobo || 0) / 100).toLocaleString(); }
  function statusBadge(s) {
    const cls = ["active", "unused"].includes(s) ? (s === "active" ? "ok" : "idle") : "off";
    return `<span class="badge ${cls}">${s}</span>`;
  }
  function esc(s) { return String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

  async function api(path, opts = {}) {
    const headers = { ...(opts.headers || {}) };
    if (token()) headers.Authorization = "Bearer " + token();
    const r = await fetch(API + path, { ...opts, headers });
    if (r.status === 401) { showLogin(); throw new Error("Session expired"); }
    if (!r.ok) { const text = await r.text(); throw new Error(text || r.statusText); }
    return r.json();
  }

  function showLogin() {
    document.getElementById("login-screen").classList.remove("hidden");
    document.getElementById("app-shell").classList.add("hidden");
  }
  function showApp() {
    document.getElementById("login-screen").classList.add("hidden");
    document.getElementById("app-shell").classList.remove("hidden");
    document.getElementById("logout-btn").classList.remove("hidden");
  }
  function navigate(pageId) {
    Object.entries(PAGES).forEach(([id, p]) => {
      document.getElementById(p.el)?.classList.toggle("hidden", id !== pageId);
      document.querySelectorAll(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.page === pageId));
    });
    document.getElementById("page-title").textContent = PAGES[pageId]?.title || "Admin";
    if (pageId === "overview") loadOverview().catch(console.error);
    if (pageId === "devices") loadDevices().catch(console.error);
    if (pageId === "sessions") loadSessions().catch(console.error);
    if (pageId === "vouchers") loadVouchers().catch(console.error);
    if (pageId === "network") {
      window.ZyranetTopologyEditor?.loadDocument().catch(console.error);
      loadNetworkMap(false).catch(console.error);
      startMapAutoRefresh();
    } else stopMapAutoRefresh();
  }
  function setMapAutoRefresh(on) { if (on) startMapAutoRefresh(); else stopMapAutoRefresh(); }

  async function savePositions(positions) {
    await api("/network/positions", {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ positions }),
    });
    const status = document.getElementById("editor-status");
    if (status) { status.textContent = "✓ Layout saved to database & cet_topology.json"; status.className = "editor-status ok"; }
  }

  async function loadOverview() {
    const ov = await api("/admin/overview");
    document.getElementById("stats-grid").innerHTML = `
      <div class="stat-card"><div class="label">Active vouchers</div><div class="value">${ov.active_vouchers}</div></div>
      <div class="stat-card"><div class="label">Unused vouchers</div><div class="value">${ov.unused_vouchers}</div></div>
      <div class="stat-card"><div class="label">Paid transactions</div><div class="value">${ov.paid_transactions}</div></div>
      <div class="stat-card"><div class="label">Revenue</div><div class="value">${ngn(ov.revenue_kobo)}</div></div>`;
  }
  async function loadVouchers() {
    const list = await api("/admin/vouchers");
    document.getElementById("voucher-rows").innerHTML = list.map((v) => `<tr>
      <td>${v.id}</td><td><code>${v.code}</code></td><td>${v.plan}</td>
      <td>${statusBadge(v.status)}</td><td>${fmtDate(v.valid_until)}</td>
      <td class="muted">${fmtDate(v.created_at)}</td></tr>`).join("")
      || `<tr><td colspan="6" class="muted">No vouchers yet</td></tr>`;
  }
  async function loadDevices() {
    const q = document.getElementById("device-search").value.trim();
    const data = await api("/devices" + (q ? "?q=" + encodeURIComponent(q) : ""));
    document.getElementById("device-count").textContent = `(${data.total})`;
    document.getElementById("device-rows").innerHTML = data.devices.map((d) => `<tr>
      <td><code>${d.mac}</code></td><td>${d.ip || "—"}</td><td>${d.vendor || "Unknown"}</td>
      <td><a href="#" data-focus-ap="${esc(d.ap || "")}">${d.ap || "—"}</a></td>
      <td>${d.online ? `<span class="badge ok">online</span>` : `<span class="badge off">offline</span>`}</td>
      <td class="muted">${fmtDate(d.first_seen)}</td><td class="muted">${fmtDate(d.last_seen)}</td></tr>`).join("")
      || `<tr><td colspan="7" class="muted">No devices found</td></tr>`;
  }
  async function loadSessions() {
    const data = await api("/devices/sessions");
    document.getElementById("session-rows").innerHTML = data.map((s) => `<tr>
      <td><code>${s.user}</code></td><td>${s.ip || "—"}</td><td><code>${s.mac || "—"}</code></td>
      <td>${s.nas || "—"}</td><td class="muted">${fmtDate(s.start)}</td>
      <td>${s.session_time ? s.session_time + "s" : "—"}</td></tr>`).join("")
      || `<tr><td colspan="6" class="muted">No active sessions</td></tr>`;
  }

  /* ---------- Network map ---------- */
  async function loadNetworkMap(fit = true) {
    const includeClients = document.getElementById("map-clients").checked;
    const data = await api("/network/topology?include_clients=" + (includeClients ? "true" : "false"));
    renderStatPills(data);
    renderZoneChips(data);
    const res = window.ZyranetMap.setTopology(data, { fit });
    window._lastTopology = data;
    renderLinkTable(data);
    return res;
  }

  function renderStatPills(data) {
    const s = data.stats || {};
    const nodes = data.nodes || [];
    const count = (k) => nodes.filter((n) => n.kind === k).length;
    const lldp = (data.edges || []).filter((e) => e.meta?.discovered).length;
    document.getElementById("map-stats").innerHTML = `
      <div class="stat-pill"><span class="pic" style="background:rgba(59,130,246,.15)">▤</span><span class="sub"><small>Switches</small><strong>${count("switch")}</strong></span></div>
      <div class="stat-pill"><span class="pic" style="background:rgba(244,114,182,.14)">✸</span><span class="sub"><small>APs / Radios</small><strong>${count("ap") + count("radio")}</strong></span></div>
      <div class="stat-pill"><span class="pic" style="background:rgba(34,197,94,.14)">●</span><span class="sub"><small>Online clients</small><strong>${s.online_clients ?? 0}</strong></span></div>
      <div class="stat-pill"><span class="pic" style="background:rgba(251,191,36,.14)">◎</span><span class="sub"><small>Sessions</small><strong>${s.active_sessions ?? 0}</strong></span></div>
      <div class="stat-pill"><span class="pic" style="background:rgba(100,116,139,.2)">─</span><span class="sub"><small>Cables</small><strong>${s.links ?? 0}</strong></span></div>
      <div class="stat-pill"><span class="pic" style="background:rgba(6,182,212,.14)">≋</span><span class="sub"><small>LLDP</small><strong>${lldp}</strong></span></div>`;
    const zones = data.zones || [];
    document.getElementById("sidebar-zones").innerHTML = "<strong style='font-size:10px;text-transform:uppercase;letter-spacing:.06em'>Zones</strong>" +
      zones.map((z) => `<div class="zrow"><span class="zdot" style="background:${z.color || "#666"}"></span>${esc(z.label || z.id)}</div>`).join("");
  }

  function renderZoneChips(data) {
    const box = document.getElementById("zone-chips");
    if (!box || box.dataset.built) return;
    box.dataset.built = "1";
    box.innerHTML = ZONE_META.map(([id, label, color]) =>
      `<button type="button" class="zone-chip" data-zone="${id}" title="Filter ${label}"><span style="color:${color}">●</span> ${label}</button>`).join("");
    box.querySelectorAll(".zone-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const z = chip.dataset.zone;
        if (activeZones.has(z)) { activeZones.delete(z); chip.classList.remove("active"); }
        else { activeZones.add(z); chip.classList.add("active"); chip.style.background = "rgba(59,130,246,.18)"; }
        if (!activeZones.has(z)) chip.style.background = "";
        window.ZyranetMap.applyFilters({ zones: new Set(activeZones) });
      });
    });
  }

  function cableTag(e) {
    const m = e.meta?.medium || "ethernet";
    const cls = e.meta?.discovered ? "lldp" : m === "wireless" ? "wl" : m === "logical" ? "log" : "eth";
    const icon = e.meta?.discovered ? "≋ LLDP" : m === "wireless" ? "∿ wireless" : m === "logical" ? "⋯ logical" : "─ ethernet";
    return `<span class="cable-tag ${cls}">${icon}</span>`;
  }

  function uplinkPath(nodeId, topology, depth = 0) {
    if (!nodeId || depth > 6) return [];
    const edge = (topology.edges || []).find((e) => e.to === nodeId);
    if (!edge) return [nodeId];
    return [...uplinkPath(edge.from, topology, depth + 1), nodeId];
  }

  function onMapNodeSelect(nodeId, topology) {
    const el = document.getElementById("map-detail");
    const portPanel = document.getElementById("port-panel");
    if (!nodeId || !topology) {
      el.innerHTML = `<p class="muted">Click any node to trace its path: uplinks, switch ports, IPs, attached clients and live sessions.</p>
        <p class="muted">Tip: enable <strong>✎ Edit layout</strong> to drag devices — positions auto-save to DB + <code>cet_topology.json</code>.</p>`;
      if (portPanel) portPanel.innerHTML = `<p class="muted">Select a switch to see its front-panel port view.</p>`;
      document.getElementById("path-hint").textContent = "Starlink → gateway → switches → radios → APs → clients";
      return;
    }
    const node = topology.nodes.find((n) => n.id === nodeId);
    if (!node) { el.innerHTML = `<p class="muted">Unknown node</p>`; return; }
    const meta = node.meta || {};
    const icons = window.ZyranetMap.KIND_ICON || {};
    const icon = icons[node.kind] || "○";
    const zoneColor = (topology.zones || []).find((z) => z.id === node.group)?.color || "#3b82f6";
    const linked = (topology.edges || []).filter((e) => e.from === nodeId || e.to === nodeId);
    const clients = (topology.nodes || []).filter((n) => n.kind === "client" && (topology.edges || []).some((e) => e.to === n.id && e.from === nodeId));
    const path = uplinkPath(nodeId, topology);
    const pathNames = path.map((id) => (topology.nodes.find((n) => n.id === id)?.label || id).split(" (")[0]);
    document.getElementById("path-hint").textContent = pathNames.join(" → ");

    const statusPill = node.kind === "client" || node.kind === "session"
      ? `<span class="badge ok">● online</span>`
      : meta.mgmt_ip ? `<span class="badge idle">managed · ${esc(meta.mgmt_ip)}</span>` : `<span class="badge idle">${esc(node.kind)}</span>`;

    el.innerHTML = `
      <div class="node-hero">
        <div class="kind-row">
          <span class="nic" style="background:${zoneColor}22;border:1px solid ${zoneColor};color:${zoneColor}">${icon}</span>
          <div><h3>${esc(node.label)}</h3><div class="nid">${esc(nodeId)} · ${esc(node.group || "")}</div></div>
          <span style="margin-left:auto">${statusPill}</span>
        </div>
        <div class="meta-grid">
          ${meta.mgmt_ip ? `<div class="meta-cell"><small>Mgmt IP</small><span>${esc(meta.mgmt_ip)}</span></div>` : ""}
          ${meta.ip ? `<div class="meta-cell"><small>IP</small><span>${esc(meta.ip)}</span></div>` : ""}
          ${meta.mac ? `<div class="meta-cell"><small>MAC</small><span>${esc(meta.mac)}</span></div>` : ""}
          ${meta.ssid ? `<div class="meta-cell"><small>SSID</small><span>${esc(meta.ssid)}</span></div>` : ""}
          ${meta.vendor ? `<div class="meta-cell"><small>Vendor</small><span>${esc(meta.vendor)}</span></div>` : ""}
          ${meta.subtitle ? `<div class="meta-cell"><small>Role</small><span>${esc(meta.subtitle)}</span></div>` : ""}
          ${meta.ports ? `<div class="meta-cell"><small>Ports</small><span>${meta.ports} × RJ45</span></div>` : ""}
          <div class="meta-cell"><small>Cables</small><span>${linked.length}</span></div>
        </div>
        <div class="path-strip">▲ ${pathNames.map(esc).join(" → ")}</div>
        <div class="toolbar">
          <button type="button" class="btn" data-act="focus">⤢ Focus</button>
          <button type="button" class="btn" data-act="edit">✎ Edit</button>
          ${node.kind === "switch" ? `<button type="button" class="btn" data-act="ports">▤ Ports</button>` : ""}
        </div>
      </div>
      <div class="mini-head">Direct connections (${linked.length})</div>
      <ul class="peer-list">${linked.slice(0, 20).map((e) => {
        const other = e.from === nodeId ? e.to : e.from;
        const otherNode = topology.nodes.find((n) => n.id === other);
        const portLbl = [e.meta?.source_port ? "P" + e.meta.source_port : "", e.meta?.target_port ? "→ P" + e.meta.target_port : ""].join(" ").trim() || e.label || "";
        return `<li data-peer="${esc(other)}"><span style="color:${zoneColor}">▸</span><code>${esc(otherNode?.label || other)}</code><span class="cable-tag eth">${esc(portLbl)}</span>${cableTag(e)}</li>`;
      }).join("") || `<li class="muted">No cables recorded — add one in Links tab.</li>`}</ul>
      ${clients.length ? `<div class="mini-head" style="margin-top:12px">Attached clients (${clients.length})</div>` +
        clients.slice(0, 15).map((c) => `<div class="client-row"><span class="dot ok"></span><code>${esc(c.label)}</code><span class="muted" style="margin-left:auto;font-size:11px">${esc(c.meta?.ip || "")}</span></div>`).join("") : ""}`;

    el.querySelectorAll("[data-peer]").forEach((li) => li.addEventListener("click", () => {
      window.ZyranetMap.focusNode(li.dataset.peer);
    }));
    el.querySelector('[data-act="focus"]')?.addEventListener("click", () => window.ZyranetMap.focusNode(nodeId));
    el.querySelector('[data-act="edit"]')?.addEventListener("click", () => window.ZyranetTopologyEditor?.showPanel("edit"));
    el.querySelector('[data-act="ports"]')?.addEventListener("click", () => window.ZyranetTopologyEditor?.showPanel("ports"));

    // Ports tab mirrors the switch face
    if (portPanel) {
      if (node.kind === "switch") {
        const ports = topology.switch_ports?.[nodeId] || [];
        const total = meta.ports || 8;
        let face = `<div class="switch-face"><div class="face-label"><span>${esc(node.label)} · front panel</span><span>${ports.length}/${total} used</span></div><div class="port-strip">`;
        for (let i = 1; i <= total; i++) {
          const p = ports.find((x) => String(x.port) === String(i));
          const cls = !p ? "" : p.discovered ? "up lldp" : (String(p.peer || "").includes("sw-") || String(p.peer || "").includes("gw-") || String(p.peer || "").includes("ns-")) ? "up uplink" : "up";
          face += `<div class="port-jack ${cls}" title="${p ? esc(p.peer + " · " + (p.medium || "")) : "empty"}">
            <div class="pn">${i}</div><div class="led"></div>
            <div class="pp">${p ? esc(String(p.peer).split("-").pop()) + (p.discovered ? " ≋" : "") : "—"}</div></div>`;
        }
        face += `</div></div><div class="mini-head" style="margin-top:12px">Port wiring</div><ul class="peer-list">` +
          (ports.map((p) => `<li><span class="cable-tag eth">P${esc(p.port)}</span><code>${esc(p.peer)}</code><span class="muted" style="font-size:11px">${esc(p.medium || "")}${p.discovered ? " · LLDP" : ""}</span></li>`).join("") || `<li class="muted">No ports patched yet.</li>`) + `</ul>`;
        portPanel.innerHTML = face;
      } else if (linked.length) {
        portPanel.innerHTML = `<div class="mini-head">Cables on ${esc(node.label)}</div><ul class="peer-list">` +
          linked.map((e) => `<li><code>${esc(e.from === nodeId ? e.to : e.from)}</code>${cableTag(e)}<span class="cable-tag eth">${esc(e.label || [e.meta?.source_port, e.meta?.target_port].filter(Boolean).join("↔"))}</span></li>`).join("") + `</ul>`;
      } else {
        portPanel.innerHTML = `<p class="muted">No port data for this ${esc(node.kind)}. Select a switch for the front-panel view.</p>`;
      }
    }
  }

  function renderLinkTable(topology) {
    const box = document.getElementById("link-table");
    if (!box) return;
    const edges = topology.edges || [];
    document.getElementById("link-count").textContent = `(${edges.filter((e) => !(String(e.id).startsWith("lk-client-") || String(e.id).startsWith("lk-session-"))).length})`;
    const infra = edges.filter((e) => !(String(e.id).startsWith("lk-client-") || String(e.id).startsWith("lk-session-"))).slice(-40).reverse();
    box.innerHTML = infra.map((e) => {
      const lbl = e.label || [e.meta?.source_port ? "P" + e.meta.source_port : "", e.meta?.target_port ? "P" + e.meta.target_port : ""].join("→").trim();
      return `<div class="link-row"><code>${esc(e.from)}</code><span class="muted">→</span><code>${esc(e.to)}</code>
        <span class="cable-tag eth">${esc(lbl || e.meta?.medium || "")}</span>${e.meta?.discovered ? `<span class="cable-tag lldp">≋</span>` : ""}
        <button type="button" class="del" data-link="${esc(e.id)}">✕</button></div>`;
    }).join("") || `<p class="muted">No cables yet.</p>`;
    box.querySelectorAll("[data-link]").forEach((b) => b.addEventListener("click", async () => {
      if (!confirm("Delete cable " + b.dataset.link + "?")) return;
      await api("/network/links/" + encodeURIComponent(b.dataset.link), { method: "DELETE" });
      await window.ZyranetTopologyEditor?.loadDocument();
      await loadNetworkMap(false);
    }));
  }

  function startMapAutoRefresh() {
    stopMapAutoRefresh();
    mapRefreshTimer = setInterval(() => loadNetworkMap(false).catch(console.error), 30000);
  }
  function stopMapAutoRefresh() { if (mapRefreshTimer) clearInterval(mapRefreshTimer); mapRefreshTimer = null; }

  window.ZyranetAdmin = { onMapNodeSelect, navigate, api, loadNetworkMap, savePositions, setMapAutoRefresh, renderLinkTable };

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".nav-btn").forEach((b) => b.addEventListener("click", () => navigate(b.dataset.page)));
    document.getElementById("login-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const err = document.getElementById("login-err");
      err.textContent = "";
      try {
        const res = await api("/auth/login", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: document.getElementById("login-user").value, password: document.getElementById("login-pass").value }),
        });
        localStorage.setItem("zyranet_token", res.access_token);
        showApp(); navigate("network");
      } catch { err.textContent = "Invalid credentials"; }
    });
    document.getElementById("logout-btn").addEventListener("click", () => { localStorage.removeItem("zyranet_token"); showLogin(); });
    document.getElementById("refresh-overview")?.addEventListener("click", () => loadOverview().catch(console.error));
    document.getElementById("refresh-vouchers")?.addEventListener("click", () => loadVouchers().catch(console.error));
    document.getElementById("scan-devices")?.addEventListener("click", async () => {
      const btn = document.getElementById("scan-devices");
      btn.disabled = true;
      try { await api("/devices/scan", { method: "POST" }); await loadDevices(); }
      finally { btn.disabled = false; }
    });
    document.getElementById("device-search")?.addEventListener("input", debounce(() => loadDevices().catch(console.error), 400));

    // Map controls
    document.getElementById("map-refresh")?.addEventListener("click", () => loadNetworkMap(true).catch(console.error));
    document.getElementById("map-clients")?.addEventListener("change", (e) => {
      window.ZyranetMap.applyFilters({ showClients: e.target.checked });
      loadNetworkMap(false).catch(console.error);
    });
    document.getElementById("map-sessions")?.addEventListener("change", (e) => window.ZyranetMap.applyFilters({ showSessions: e.target.checked }));
    document.getElementById("tog-wireless")?.addEventListener("change", (e) => window.ZyranetMap.applyFilters({ showWireless: e.target.checked }));
    document.getElementById("tog-logical")?.addEventListener("change", (e) => window.ZyranetMap.applyFilters({ showLogical: e.target.checked }));
    document.getElementById("kind-filter")?.addEventListener("change", (e) => window.ZyranetMap.applyFilters({ kind: e.target.value }));
    document.getElementById("map-fit")?.addEventListener("click", () => window.ZyranetMap.fitView());
    document.getElementById("map-zoom-in")?.addEventListener("click", () => window.ZyranetMap.zoomIn());
    document.getElementById("map-zoom-out")?.addEventListener("click", () => window.ZyranetMap.zoomOut());
    document.getElementById("map-physics")?.addEventListener("click", () => {
      const on = window.ZyranetMap.togglePhysics();
      document.getElementById("map-physics").textContent = on ? "Physics on" : "Physics";
    });
    const search = document.getElementById("map-search");
    search?.addEventListener("input", debounce(() => {
      const q = search.value.trim();
      window.ZyranetMap.applyFilters({ search: q });
      if (q.length > 1) {
        const hits = window.ZyranetMap.searchNodes(q);
        if (hits.length === 1) window.ZyranetMap.focusNode(hits[0].id);
      }
    }, 300));
    search?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const hits = window.ZyranetMap.searchNodes(search.value.trim());
        if (hits.length) window.ZyranetMap.focusNode(hits[0].id);
      }
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "/" && document.getElementById("page-network")?.offsetParent && document.activeElement !== search) {
        e.preventDefault(); search?.focus();
      }
    });

    const mapEl = document.getElementById("network-map");
    if (mapEl) window.ZyranetMap.init(mapEl);
    window.ZyranetTopologyEditor?.bind();

    if (token()) { showApp(); navigate("network"); } else showLogin();
  });
})();
