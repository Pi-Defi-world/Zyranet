/** Packet Tracer-style network map: layered devices, port-labelled cables, filters. */
(function (global) {
  const KIND_ICON = {
    wan: "◉", router: "▣", switch: "▤", server: "▦",
    radio: "◈", ap: "✸", service: "⬢", client: "●",
    session: "◎", unknown: "○",
  };
  const KIND_NAME = {
    wan: "WAN uplink", router: "Router", switch: "Switch", server: "Server",
    radio: "PtMP radio", ap: "Access point", service: "Service",
    client: "Client device", session: "RADIUS session", unknown: "Device",
  };
  const ZONE_COLORS = {
    internet: { background: "#3a4358", border: "#94a3b8", highlight: { background: "#4b586f", border: "#cbd5e1" } },
    core: { background: "#16294d", border: "#3b82f6", highlight: { background: "#1d4ed8", border: "#93c5fd" } },
    admin: { background: "#2b2350", border: "#a78bfa", highlight: { background: "#5b21b6", border: "#c4b5fd" } },
    guest: { background: "#0f3a24", border: "#22c55e", highlight: { background: "#15803d", border: "#4ade80" } },
    "bldg-a": { background: "#4a2c0c", border: "#fbbf24", highlight: { background: "#92400e", border: "#fde68a" } },
    "bldg-b": { background: "#4c1d0c", border: "#fb923c", highlight: { background: "#9a3412", border: "#fed7aa" } },
    "bldg-c": { background: "#4c0f28", border: "#f472b6", highlight: { background: "#9d174d", border: "#fbcfe8" } },
  };
  const KIND_SHAPE = { wan: "ellipse", router: "box", switch: "box", server: "box", radio: "diamond", ap: "star", service: "ellipse", client: "dot", session: "dot", unknown: "dot" };

  let network = null;
  let nodesDataSet = null;
  let edgesDataSet = null;
  let lastTopology = null;
  let physicsEnabled = false;
  let layoutEditMode = false;
  let saveTimer = null;
  let selectedId = null;
  const pendingPositions = {};
  const filters = {
    zones: new Set(), kind: "", showClients: true, showSessions: true,
    showWireless: true, showLogical: true, search: "",
  };

  function isInfraNode(id) {
    return id && !String(id).startsWith("client-") && !String(id).startsWith("session-");
  }
  function isClientNode(n) { return n.kind === "client" || String(n.id).startsWith("client-"); }
  function isSessionNode(n) { return n.kind === "session" || String(n.id).startsWith("session-"); }

  function nodePasses(n) {
    if (filters.zones.size && !filters.zones.has(n.group)) return false;
    if (filters.kind && n.kind !== filters.kind) return false;
    if (!filters.showClients && isClientNode(n)) return false;
    if (!filters.showSessions && isSessionNode(n)) return false;
    if (filters.search) {
      const q = filters.search.toLowerCase();
      const hay = [n.id, n.label, n.meta?.mgmt_ip, n.meta?.ip, n.meta?.mac, n.meta?.ssid, KIND_NAME[n.kind]]
        .filter(Boolean).join(" ").toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  }
  function edgePasses(e, visibleIds) {
    if (!visibleIds.has(e.from) || !visibleIds.has(e.to)) return false;
    const m = e.meta?.medium || (e.dashes ? "wireless" : "ethernet");
    if (m === "wireless" && !filters.showWireless) return false;
    if (m === "logical" && !filters.showLogical) return false;
    return true;
  }

  function styleNode(n) {
    const c = ZONE_COLORS[n.group] || ZONE_COLORS.core;
    const icon = KIND_ICON[n.kind] || KIND_ICON.unknown;
    const sub = n.meta?.mgmt_ip || n.meta?.ip || n.meta?.subtitle || n.meta?.ssid || KIND_NAME[n.kind] || "";
    const out = {
      ...n,
      shape: KIND_SHAPE[n.kind] || "dot",
      color: n.color || c,
      font: {
        color: "#e8edf7",
        size: n.kind === "client" || n.kind === "session" ? 11 : 14,
        face: "IBM Plex Sans",
        multi: true,
      },
      label: `${icon}  ${n.label}${sub ? `\n<i>${sub}</i>` : ""}`,
      borderWidth: 2,
      size: n.kind === "switch" ? 30 : n.kind === "router" || n.kind === "server" ? 28 : n.kind === "client" || n.kind === "session" ? 12 : 24,
    };
    if (out.shape === "box") { out.shapeProperties = { borderRadius: 7 }; out.margin = 12; }
    if (layoutEditMode && isInfraNode(n.id)) out.fixed = false;
    if (n.kind === "client") {
      out.color = { background: "#0f3a24", border: "#22c55e", highlight: { background: "#15803d", border: "#4ade80" } };
      out.borderWidth = 2;
    }
    if (n.kind === "session") {
      out.color = { background: "#3a2c08", border: "#fbbf24", highlight: { background: "#92400e", border: "#fde68a" } };
    }
    if (selectedId && n.id === selectedId) out.borderWidth = 4;
    return out;
  }

  function styleEdge(e) {
    const medium = e.meta?.medium || "ethernet";
    const out = { ...e, width: 2, font: { color: "#aeb9d2", size: 11, strokeWidth: 0, align: "middle" } };
    if (medium === "ethernet") { out.color = { color: e.meta?.discovered ? "#06b6d4" : "#7d8aa5" }; out.dashes = !!e.meta?.discovered; out.width = 2.5; }
    else if (medium === "wireless") { out.color = { color: "#38bdf8" }; out.dashes = [6, 4]; out.width = 2; }
    else if (medium === "logical") { out.color = { color: "#a78bfa" }; out.dashes = [3, 4]; out.width = 1.6; }
    if (e.id && String(e.id).startsWith("lk-client-")) { out.color = { color: "#22c55e" }; out.dashes = [4, 4]; out.width = 1.4; }
    if (e.id && String(e.id).startsWith("lk-session-")) { out.color = { color: "#fbbf24" }; out.dashes = [3, 4]; out.width = 1.3; }
    if (selectedId && (e.from === selectedId || e.to === selectedId)) { out.width = 3.5; }
    else if (selectedId) { out.color = { color: "#26334f" }; out.font = { color: "#4b5a78", size: 10, strokeWidth: 0 }; }
    return out;
  }

  function flushPositions() {
    const keys = Object.keys(pendingPositions);
    if (!keys.length || !global.ZyranetAdmin?.savePositions) return;
    const batch = { ...pendingPositions };
    keys.forEach((k) => delete pendingPositions[k]);
    const badge = document.getElementById("save-badge");
    if (badge) badge.classList.remove("hidden");
    global.ZyranetAdmin.savePositions(batch)
      .catch(console.error)
      .finally(() => { if (badge) badge.classList.add("hidden"); });
  }
  function queuePosition(id, x, y) {
    pendingPositions[id] = { x: Math.round(x), y: Math.round(y) };
    clearTimeout(saveTimer);
    saveTimer = setTimeout(flushPositions, 600);
  }

  function init(container) {
    if (!global.vis) { console.error("vis-network not loaded"); return; }
    nodesDataSet = new vis.DataSet([]);
    edgesDataSet = new vis.DataSet([]);
    network = new vis.Network(container, { nodes: nodesDataSet, edges: edgesDataSet }, {
      interaction: { hover: true, multiselect: false, navigationButtons: false, keyboard: true, tooltipDelay: 120 },
      physics: { enabled: false },
      layout: { improvedLayout: false },
      nodes: { borderWidth: 2, shadow: { enabled: true, size: 10, x: 0, y: 3, color: "rgba(0,0,0,0.45)" } },
      edges: { smooth: { type: "cubicBezier", forceDirection: "vertical", roundness: 0.35 }, arrows: { to: { enabled: true, scaleFactor: 0.7 } } },
    });
    network.on("click", (params) => {
      if (params.nodes.length) {
        selectedId = params.nodes[0];
        repaintHighlight();
        global.ZyranetAdmin?.onMapNodeSelect(selectedId, lastTopology);
        global.ZyranetTopologyEditor?.onNodeSelected(selectedId, lastTopology);
      } else {
        selectedId = null;
        repaintHighlight();
        global.ZyranetAdmin?.onMapNodeSelect(null, lastTopology);
      }
    });
    network.on("hoverNode", (params) => {
      const bar = document.getElementById("map-hoverbar");
      if (!bar || !lastTopology) return;
      const n = lastTopology.nodes.find((x) => x.id === params.node);
      if (!n) return;
      const deg = (lastTopology.edges || []).filter((e) => e.from === n.id || e.to === n.id).length;
      bar.textContent = `${n.label} · ${KIND_NAME[n.kind] || n.kind} · ${deg} cable${deg === 1 ? "" : "s"}`;
      bar.classList.remove("hidden");
    });
    network.on("blurNode", () => document.getElementById("map-hoverbar")?.classList.add("hidden"));
    network.on("doubleClick", (params) => {
      if (params.nodes.length) network.focus(params.nodes[0], { scale: 1.25, animation: true });
    });
    network.on("dragEnd", (params) => {
      if (!layoutEditMode || !params.nodes.length) return;
      const id = params.nodes[0];
      if (!isInfraNode(id)) return;
      const pos = network.getPositions([id])[id];
      if (pos) queuePosition(id, pos.x, pos.y);
    });
  }

  function repaintHighlight() {
    if (!lastTopology || !nodesDataSet) return;
    const visible = new Set(nodesDataSet.getIds());
    try {
      lastTopology.nodes.filter((n) => visible.has(n.id)).forEach((n) => {
        nodesDataSet.update({ id: n.id, borderWidth: n.id === selectedId ? 4 : 2 });
      });
      lastTopology.edges.filter((e) => visible.has(e.from) && visible.has(e.to)).forEach((e) => {
        if (!edgesDataSet.get(e.id)) return;
        const medium = e.meta?.medium || "ethernet";
        let color = "#7d8aa5";
        if (e.id && String(e.id).startsWith("lk-client-")) color = "#22c55e";
        else if (e.id && String(e.id).startsWith("lk-session-")) color = "#fbbf24";
        else if (medium === "wireless") color = "#38bdf8";
        else if (medium === "logical") color = "#a78bfa";
        else if (e.meta?.discovered) color = "#06b6d4";
        if (selectedId && e.from !== selectedId && e.to !== selectedId) color = "#26334f";
        edgesDataSet.update({ id: e.id, color: { color }, width: selectedId && (e.from === selectedId || e.to === selectedId) ? 3.5 : undefined });
      });
    } catch (_) { /* dataset race — ignore */ }
  }

  function setTopology(data, opts = {}) {
    const fit = opts.fit !== false;
    lastTopology = data;
    const nodes = (data.nodes || []).filter(nodePasses).map(styleNode);
    const visibleIds = new Set(nodes.map((n) => n.id));
    const edges = (data.edges || []).filter((e) => edgePasses(e, visibleIds)).map(styleEdge);
    const positions = layoutEditMode && network ? network.getPositions() : null;
    nodesDataSet.clear();
    edgesDataSet.clear();
    nodesDataSet.add(nodes);
    edgesDataSet.add(edges);
    if (layoutEditMode && positions) {
      Object.keys(positions).forEach((id) => {
        if (nodesDataSet.get(id)) nodesDataSet.update({ id, x: positions[id].x, y: positions[id].y, fixed: false });
      });
    }
    if (!physicsEnabled) network.setOptions({ physics: { enabled: false } });
    if (fit) network.fit({ animation: { duration: 400, easingFunction: "easeInOutQuad" } });
    return { shownNodes: nodes.length, shownEdges: edges.length };
  }

  function applyFilters(next) {
    Object.assign(filters, next);
    if (lastTopology) setTopology(lastTopology, { fit: false });
  }
  function focusNode(id) {
    if (!id || !nodesDataSet.get(id)) return false;
    selectedId = id;
    repaintHighlight();
    network.focus(id, { scale: 1.25, animation: true });
    global.ZyranetAdmin?.onMapNodeSelect(id, lastTopology);
    return true;
  }
  function searchNodes(q) {
    if (!lastTopology) return [];
    const s = q.toLowerCase();
    return lastTopology.nodes
      .filter((n) => [n.id, n.label, n.meta?.mgmt_ip, n.meta?.ip, n.meta?.mac].filter(Boolean).join(" ").toLowerCase().includes(s))
      .slice(0, 8);
  }
  function toggleLayoutEdit() {
    layoutEditMode = !layoutEditMode;
    nodesDataSet.getIds().filter(isInfraNode).forEach((id) => nodesDataSet.update({ id, fixed: !layoutEditMode }));
    if (!layoutEditMode) flushPositions();
    return layoutEditMode;
  }
  function fitView() { network?.fit({ animation: true }); }
  function zoomIn() { const s = network.getScale(); network.moveTo({ scale: s * 1.25, animation: true }); }
  function zoomOut() { const s = network.getScale(); network.moveTo({ scale: s / 1.25, animation: true }); }
  function togglePhysics() {
    physicsEnabled = !physicsEnabled;
    network.setOptions({ physics: { enabled: physicsEnabled, barnesHut: { gravitationalConstant: -8000 } } });
    return physicsEnabled;
  }

  global.ZyranetMap = {
    init, setTopology, fitView, zoomIn, zoomOut, togglePhysics, toggleLayoutEdit,
    applyFilters, focusNode, searchNodes, KIND_NAME, KIND_ICON,
    get selectedId() { return selectedId; },
  };
})(window);
