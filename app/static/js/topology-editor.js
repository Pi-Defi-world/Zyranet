/** Topology CRUD + SNMP discovery + link manager (works with NOC inspector). */
(function (global) {
  let rawDocument = null;
  let lastSuggestions = [];

  function api(path, opts) { return global.ZyranetAdmin.api(path, opts); }

  function nodeOptions(selected) {
    const nodes = (rawDocument?.nodes || []).slice().sort((a, b) => a.label.localeCompare(b.label));
    return nodes.map((n) => `<option value="${n.id}" ${n.id === selected ? "selected" : ""}>${n.label} (${n.id})</option>`).join("");
  }

  async function loadDocument() {
    const res = await api("/network/document");
    rawDocument = res.document;
    refreshLinkSelects();
    return rawDocument;
  }

  function refreshLinkSelects() {
    const src = document.getElementById("link-source");
    const tgt = document.getElementById("link-target");
    if (src) src.innerHTML = nodeOptions(src.value || "sw-core");
    if (tgt) tgt.innerHTML = nodeOptions(tgt.value || "sw-bldg-a");
  }

  function fillNodeForm(nodeId) {
    const n = (rawDocument?.nodes || []).find((x) => x.id === nodeId);
    if (!n) return;
    document.getElementById("edit-node-id").value = n.id;
    document.getElementById("edit-node-label").value = n.label || "";
    document.getElementById("edit-node-kind").value = n.kind || "unknown";
    document.getElementById("edit-node-zone").value = n.zone || "core";
    document.getElementById("edit-node-subtitle").value = n.subtitle || "";
    document.getElementById("edit-node-mgmt-ip").value = n.mgmt_ip || "";
    document.getElementById("edit-node-ports").value = n.ports ?? "";
    document.getElementById("edit-node-ssid").value = n.ssid || "";
  }

  function showPanel(name) {
    document.querySelectorAll(".side-tab").forEach((b) => b.classList.toggle("active", b.dataset.panel === name));
    document.querySelectorAll(".side-panel").forEach((p) => p.classList.toggle("hidden", p.dataset.panel !== name));
  }

  function setStatus(msg, ok) {
    const el = document.getElementById("editor-status");
    if (!el) return;
    el.textContent = msg;
    el.className = "editor-status muted" + (ok === true ? " ok" : ok === false ? " err" : "");
    clearTimeout(setStatus._t);
    setStatus._t = setTimeout(() => { if (el.textContent === msg) { el.textContent = ""; el.className = "editor-status muted"; } }, 4500);
  }
  function fail(e) { setStatus(parseErr(e), false); }
  function parseErr(e) {
    const m = String(e?.message || e || "Request failed");
    try { const j = JSON.parse(m.slice(m.indexOf("{"))); return j.detail || m.slice(0, 160); } catch { return m.slice(0, 200); }
  }

  async function saveNodeForm(isNew) {
    const id = document.getElementById("edit-node-id").value.trim();
    const label = document.getElementById("edit-node-label").value.trim();
    if (!id || !label) { setStatus("Node ID and Label are required.", false); return; }
    const payload = {
      id, label,
      kind: document.getElementById("edit-node-kind").value,
      zone: document.getElementById("edit-node-zone").value,
      subtitle: document.getElementById("edit-node-subtitle").value.trim() || null,
      mgmt_ip: document.getElementById("edit-node-mgmt-ip").value.trim() || null,
      ssid: document.getElementById("edit-node-ssid").value.trim() || null,
    };
    const ports = document.getElementById("edit-node-ports").value;
    if (ports) payload.ports = parseInt(ports, 10);
    if (isNew) {
      await api("/network/nodes", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    } else {
      await api("/network/nodes/" + encodeURIComponent(id), { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    }
    await loadDocument();
    await global.ZyranetAdmin.loadNetworkMap(false);
    setStatus(isNew ? `✓ Node ${id} created.` : `✓ Node ${id} saved.`, true);
  }

  async function deleteSelectedNode() {
    const id = document.getElementById("edit-node-id").value.trim();
    if (!id || !confirm(`Delete ${id} and all its cables?`)) return;
    await api("/network/nodes/" + encodeURIComponent(id), { method: "DELETE" });
    await loadDocument();
    await global.ZyranetAdmin.loadNetworkMap(false);
    setStatus(`Node ${id} deleted.`, true);
  }

  async function saveLinkForm() {
    const payload = {
      source: document.getElementById("link-source").value,
      target: document.getElementById("link-target").value,
      source_port: document.getElementById("link-source-port").value.trim() || null,
      target_port: document.getElementById("link-target-port").value.trim() || null,
      medium: document.getElementById("link-medium").value,
      label: document.getElementById("link-label").value.trim() || null,
    };
    if (!payload.source || !payload.target) { setStatus("Pick both endpoints.", false); return; }
    if (payload.source === payload.target) { setStatus("Endpoints must differ.", false); return; }
    await api("/network/links", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    document.getElementById("link-source-port").value = "";
    document.getElementById("link-target-port").value = "";
    document.getElementById("link-label").value = "";
    await loadDocument();
    await global.ZyranetAdmin.loadNetworkMap(false);
    setStatus(`✓ Cable ${payload.source} → ${payload.target} added.`, true);
  }

  function renderDiscoveryResults(data) {
    const box = document.getElementById("discovery-results");
    if (!box) return;
    if (!data.ok && data.error) { box.innerHTML = `<p class="err">Discovery failed: ${data.error} — is pysnmp installed and SNMP_TARGETS reachable?</p>`; return; }
    lastSuggestions = data.suggestions || [];
    let html = "";
    (data.results || []).forEach((r) => {
      html += `<div class="disc-block"><strong>${r.host}</strong> ${r.node_id ? `<span class="badge idle">${r.node_id}</span>` : ""} ${r.ok ? `<span class="badge ok">ok</span>` : `<span class="badge off">${r.error || "fail"}</span>`}`;
      if (r.neighbors?.length) {
        html += "<ul>";
        r.neighbors.forEach((n) => { html += `<li>Port <code>${n.local_port}</code> → <code>${n.remote_sys_name}</code> ${n.remote_port_desc ? "(" + n.remote_port_desc + ")" : ""}</li>`; });
        html += "</ul>";
      } else if (r.interfaces_up?.length) {
        html += `<p class="muted">No LLDP — ${r.interfaces_up.length} interfaces up (IF-MIB): ${r.interfaces_up.slice(0, 8).join(", ")}</p>`;
      } else if (r.ok) html += `<p class="muted">No LLDP neighbors reported.</p>`;
      html += "</div>";
    });
    html += `<p class="muted">${lastSuggestions.length} cable suggestion(s) matched to known devices.</p>`;
    if (lastSuggestions.length) html += `<button type="button" class="btn primary" id="apply-discovery">Apply ${lastSuggestions.length} suggestion(s)</button>`;
    box.innerHTML = html;
    document.getElementById("apply-discovery")?.addEventListener("click", applyDiscovery);
  }

  async function runSnmpDiscovery() {
    setStatus("Running SNMP/LLDP…");
    const box = document.getElementById("discovery-results");
    if (box) box.innerHTML = `<p class="muted">Querying switches (2s timeout each)…</p>`;
    try {
      const data = await api("/network/discover/snmp", { method: "POST" });
      renderDiscoveryResults(data);
      setStatus("Discovery finished.", true);
    } catch (e) { if (box) box.innerHTML = `<p class="err">${parseErr(e)}</p>`; setStatus(parseErr(e), false); }
  }

  async function applyDiscovery() {
    if (!lastSuggestions.length) return;
    const res = await api("/network/discover/apply", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ links: lastSuggestions }),
    });
    await loadDocument();
    await global.ZyranetAdmin.loadNetworkMap(false);
    setStatus(`✓ Applied ${res.count} LLDP cable(s).`, true);
  }

  function onNodeSelected(nodeId, topology) {
    if (!nodeId || String(nodeId).startsWith("client-") || String(nodeId).startsWith("session-")) return;
    fillNodeForm(nodeId);
  }

  function bind() {
    document.querySelectorAll(".side-tab").forEach((b) => b.addEventListener("click", () => showPanel(b.dataset.panel)));
    document.getElementById("btn-save-node")?.addEventListener("click", () => saveNodeForm(false).catch(fail));
    document.getElementById("btn-new-node")?.addEventListener("click", () => {
      ["edit-node-id", "edit-node-label", "edit-node-subtitle", "edit-node-mgmt-ip", "edit-node-ports", "edit-node-ssid"].forEach((id) => { document.getElementById(id).value = ""; });
      showPanel("edit");
      document.getElementById("edit-node-id")?.focus();
    });
    document.getElementById("btn-create-node")?.addEventListener("click", () => saveNodeForm(true).catch(fail));
    document.getElementById("btn-delete-node")?.addEventListener("click", () => deleteSelectedNode().catch(fail));
    document.getElementById("btn-save-link")?.addEventListener("click", () => saveLinkForm().catch(fail));
    document.getElementById("btn-snmp-discover")?.addEventListener("click", () => runSnmpDiscovery());
    document.getElementById("btn-export-json")?.addEventListener("click", async () => {
      try { const r = await api("/network/export-file", { method: "POST" }); setStatus("Exported to " + r.path, true); }
      catch (e) { fail(e); }
    });
    document.getElementById("map-layout-edit")?.addEventListener("click", () => {
      const on = global.ZyranetMap.toggleLayoutEdit();
      const btn = document.getElementById("map-layout-edit");
      btn.classList.toggle("primary", on);
      btn.textContent = on ? "● Saving layout…" : "✎ Edit layout";
      global.ZyranetAdmin.setMapAutoRefresh(!on);
      setStatus(on ? "Drag devices — positions auto-save." : "Layout locked.", true);
    });
  }

  global.ZyranetTopologyEditor = { loadDocument, onNodeSelected, showPanel, bind };
})(window);
