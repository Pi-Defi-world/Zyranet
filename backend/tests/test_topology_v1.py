"""v1 topology API: document edits, node/link CRUD, discovery endpoints, audit."""
from __future__ import annotations


async def test_document_roundtrip_and_audit(client, auth_headers):
    resp = await client.put(
        "/api/v1/topology/document",
        json={"document": {"nodes": [], "links": [], "zones": [], "meta": {"name": "test"}}},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["updated_at"] is not None
    assert resp.json()["document"]["nodes"] == []

    got = await client.get("/api/v1/topology/document", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["document"]["meta"]["name"] == "test"

    events = await client.get("/api/v1/audit-events?action=topology.document", headers=auth_headers)
    assert events.status_code == 200
    assert events.json()["total"] >= 1
    assert events.json()["items"][0]["action"] == "topology.document.save"


async def test_node_and_link_crud(client, auth_headers):
    # Minimal document so node/link tests do not depend on the seed file.
    await client.put(
        "/api/v1/topology/document",
        json={"document": {"nodes": [], "links": [], "zones": []}},
        headers=auth_headers,
    )

    node = await client.post(
        "/api/v1/topology/nodes",
        json={"id": "sw-test-1", "label": "Test Switch", "kind": "switch", "mgmt_ip": "10.9.9.1"},
        headers=auth_headers,
    )
    assert node.status_code == 201, node.text

    dup = await client.post(
        "/api/v1/topology/nodes",
        json={"id": "sw-test-1", "label": "Again"},
        headers=auth_headers,
    )
    assert dup.status_code == 409

    other = await client.post(
        "/api/v1/topology/nodes",
        json={"id": "sw-test-2", "label": "Second Switch", "kind": "switch"},
        headers=auth_headers,
    )
    assert other.status_code == 201

    # Link with a missing endpoint must be rejected.
    bad_link = await client.post(
        "/api/v1/topology/links",
        json={"source": "sw-test-1", "target": "ghost"},
        headers=auth_headers,
    )
    assert bad_link.status_code == 400

    link = await client.post(
        "/api/v1/topology/links",
        json={"source": "sw-test-1", "target": "sw-test-2", "source_port": "1", "target_port": "2"},
        headers=auth_headers,
    )
    assert link.status_code == 201, link.text
    link_id = link.json()["id"]

    renamed = await client.put(
        "/api/v1/topology/nodes/sw-test-2",
        json={"id": "sw-test-2", "label": "Renamed Switch"},
        headers=auth_headers,
    )
    assert renamed.status_code == 200
    assert renamed.json()["label"] == "Renamed Switch"

    moved = await client.patch(
        "/api/v1/topology/positions",
        json={"positions": {"sw-test-1": {"x": 120.0, "y": 240.0}}},
        headers=auth_headers,
    )
    assert moved.status_code == 200
    assert moved.json() == {"updated": 1}

    doc = (await client.get("/api/v1/topology/document", headers=auth_headers)).json()["document"]
    by_id = {n["id"]: n for n in doc["nodes"]}
    assert by_id["sw-test-1"]["fixed"] == {"x": 120.0, "y": 240.0}

    del_link = await client.delete(f"/api/v1/topology/links/{link_id}", headers=auth_headers)
    assert del_link.status_code == 200

    del_node = await client.delete("/api/v1/topology/nodes/sw-test-1", headers=auth_headers)
    assert del_node.status_code == 200
    gone = await client.delete("/api/v1/topology/nodes/sw-test-1", headers=auth_headers)
    assert gone.status_code == 404

    events = await client.get("/api/v1/audit-events?action=topology.", headers=auth_headers)
    actions = {e["action"] for e in events.json()["items"]}
    assert {
        "topology.node.create",
        "topology.node.update",
        "topology.node.delete",
        "topology.link.create",
        "topology.link.delete",
        "topology.position.update",
    } <= actions


async def test_graph_endpoint_smoke(client, auth_headers):
    resp = await client.get("/api/v1/topology/graph", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "nodes" in body and "edges" in body


async def test_discovery_run_requires_snmp_config(client, auth_headers, monkeypatch):
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "snmp_enabled", False, raising=False)
    resp = await client.post("/api/v1/topology/discovery/run", headers=auth_headers)
    assert resp.status_code == 400
    assert "SNMP_ENABLED" in resp.json()["detail"]

    monkeypatch.setattr(settings, "snmp_enabled", True, raising=False)
    monkeypatch.setattr(settings, "snmp_targets", "  ", raising=False)
    resp = await client.post("/api/v1/topology/discovery/run", headers=auth_headers)
    assert resp.status_code == 400
    assert "SNMP_TARGETS" in resp.json()["detail"]


async def test_discovery_apply_and_audit(client, auth_headers):
    await client.put(
        "/api/v1/topology/document",
        json={"document": {"nodes": [], "links": [], "zones": []}},
        headers=auth_headers,
    )
    for nid in ("sw-a", "sw-b"):
        await client.post(
            "/api/v1/topology/nodes",
            json={"id": nid, "label": nid.upper()},
            headers=auth_headers,
        )

    resp = await client.post(
        "/api/v1/topology/discovery/apply",
        json={
            "links": [
                {"source": "sw-a", "target": "sw-b", "source_port": "1", "target_port": "2"},
                {"source": "sw-a", "target": "sw-b", "source_port": "1", "target_port": "2"},
            ]
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["count"] == 1  # duplicate suggestion collapsed

    # Applying the same pair again adds nothing (dedup against stored links).
    again = await client.post(
        "/api/v1/topology/discovery/apply",
        json={
            "links": [
                {"source": "sw-a", "target": "sw-b", "source_port": "1", "target_port": "2"}
            ]
        },
        headers=auth_headers,
    )
    assert again.json()["count"] == 0

    events = await client.get(
        "/api/v1/audit-events?action=topology.discovery", headers=auth_headers
    )
    assert events.json()["total"] >= 1
    assert events.json()["items"][0]["action"] == "topology.discovery.apply"
