"""v1 inventory API tests: locations, models, devices, audit trail."""
from __future__ import annotations


async def test_locations_crud_and_hierarchy(client, auth_headers):
    parent = await client.post(
        "/api/v1/locations",
        json={"kind": "site", "name": "Main Campus", "code": "MAIN"},
        headers=auth_headers,
    )
    assert parent.status_code == 201
    site_id = parent.json()["id"]

    child = await client.post(
        "/api/v1/locations",
        json={"kind": "building", "name": "Library", "parent_id": site_id},
        headers=auth_headers,
    )
    assert child.status_code == 201
    assert child.json()["parent_id"] == site_id

    listed = await client.get("/api/v1/locations?kind=building", headers=auth_headers)
    assert listed.status_code == 200
    assert [x["name"] for x in listed.json()] == ["Library"]

    patched = await client.patch(
        f"/api/v1/locations/{site_id}", json={"notes": "audited 2026"}, headers=auth_headers
    )
    assert patched.status_code == 200
    assert patched.json()["notes"] == "audited 2026"
    assert patched.json()["name"] == "Main Campus"  # untouched

    # Parent must exist.
    bad = await client.post(
        "/api/v1/locations", json={"kind": "room", "name": "R1", "parent_id": 9999},
        headers=auth_headers,
    )
    assert bad.status_code == 422

    # Cannot delete a location that still has children.
    blocked = await client.delete(f"/api/v1/locations/{site_id}", headers=auth_headers)
    assert blocked.status_code == 409

    child_id = child.json()["id"]
    ok = await client.delete(f"/api/v1/locations/{child_id}", headers=auth_headers)
    assert ok.status_code == 204
    gone = await client.get(f"/api/v1/locations/{child_id}", headers=auth_headers)
    assert gone.status_code == 404


async def test_device_model_with_capabilities(client, auth_headers):
    resp = await client.post(
        "/api/v1/device-models",
        json={
            "vendor": "Ubiquiti Networks",
            "model": "NanoStation M2",
            "family": "airMAX",
            "support_status": "supported",
            "capabilities": [
                {"capability": "identify", "support_level": "read"},
                {"capability": "inspect", "support_level": "read", "adapter": "airos"},
                {"capability": "configure", "support_level": "guided_manual"},
            ],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    model_id = body["id"]
    assert {c["capability"] for c in body["capabilities"]} == {
        "identify",
        "inspect",
        "configure",
    }

    fetched = await client.get(f"/api/v1/device-models/{model_id}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["family"] == "airMAX"

    duplicate = await client.post(
        "/api/v1/device-models",
        json={"vendor": "Ubiquiti Networks", "model": "NanoStation M2"},
        headers=auth_headers,
    )
    assert duplicate.status_code == 409

    page = await client.get("/api/v1/device-models?q=nanostation", headers=auth_headers)
    assert page.status_code == 200
    assert page.json()["total"] == 1


async def test_device_create_list_patch_delete(client, auth_headers):
    loc = await client.post(
        "/api/v1/locations", json={"kind": "building", "name": "Science Block"},
        headers=auth_headers,
    )
    location_id = loc.json()["id"]
    model = await client.post(
        "/api/v1/device-models",
        json={"vendor": "TP-Link", "model": "CPE610"},
        headers=auth_headers,
    )
    model_id = model.json()["id"]

    created = await client.post(
        "/api/v1/devices",
        json={
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "label": "Roof station",
            "vendor": "TP-Link",
            "type": "ap",
            "model_id": model_id,
            "location_id": location_id,
            "role": "station-bridge",
            "condition": "unverified",
            "interfaces": [{"name": "eth0", "kind": "ethernet", "link_state": "up"}],
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    device = created.json()
    device_id = device["id"]
    assert device["mac_address"] == "aa:bb:cc:dd:ee:ff"  # normalised
    assert device["model"]["model"] == "CPE610"
    assert device["location"]["name"] == "Science Block"

    # Duplicate MAC is rejected.
    dup = await client.post(
        "/api/v1/devices", json={"mac_address": "aa:bb:cc:dd:ee:ff"},
        headers=auth_headers,
    )
    assert dup.status_code == 409

    # Invalid MAC shape is a validation error, not a DB error.
    invalid = await client.post(
        "/api/v1/devices", json={"mac_address": "not-a-mac"}, headers=auth_headers
    )
    assert invalid.status_code == 422

    # Filters + pagination shape.
    page = await client.get(
        f"/api/v1/devices?location_id={location_id}&type=ap&limit=10", headers=auth_headers
    )
    assert page.status_code == 200
    assert page.json()["total"] == 1
    assert page.json()["items"][0]["id"] == device_id

    search = await client.get("/api/v1/devices?q=roof", headers=auth_headers)
    assert search.json()["total"] == 1

    # Patch touches only the provided fields.
    patched = await client.patch(
        f"/api/v1/devices/{device_id}",
        json={"condition": "good", "identity_confidence": "confirmed", "firmware": "v8.7"},
        headers=auth_headers,
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["condition"] == "good"
    assert body["firmware"] == "v8.7"
    assert body["label"] == "Roof station"

    # Unknown references are rejected.
    bad_ref = await client.patch(
        f"/api/v1/devices/{device_id}", json={"location_id": 424242}, headers=auth_headers
    )
    assert bad_ref.status_code == 422

    deleted = await client.delete(f"/api/v1/devices/{device_id}", headers=auth_headers)
    assert deleted.status_code == 204
    gone = await client.get(f"/api/v1/devices/{device_id}", headers=auth_headers)
    assert gone.status_code == 404


async def test_interfaces_lifecycle(client, auth_headers):
    device = await client.post(
        "/api/v1/devices", json={"mac_address": "11:22:33:44:55:66"},
        headers=auth_headers,
    )
    device_id = device.json()["id"]

    iface = await client.post(
        f"/api/v1/devices/{device_id}/interfaces",
        json={"name": "ath0", "kind": "radio", "link_state": "up", "speed_mbps": 150},
        headers=auth_headers,
    )
    assert iface.status_code == 201
    iface_id = iface.json()["id"]

    dup = await client.post(
        f"/api/v1/devices/{device_id}/interfaces", json={"name": "ath0"},
        headers=auth_headers,
    )
    assert dup.status_code == 409

    listed = await client.get(f"/api/v1/devices/{device_id}/interfaces", headers=auth_headers)
    assert [x["name"] for x in listed.json()] == ["ath0"]

    patched = await client.patch(
        f"/api/v1/devices/{device_id}/interfaces/{iface_id}",
        json={"name": "ath0", "kind": "radio", "link_state": "down"},
        headers=auth_headers,
    )
    assert patched.json()["link_state"] == "down"

    removed = await client.delete(
        f"/api/v1/devices/{device_id}/interfaces/{iface_id}", headers=auth_headers
    )
    assert removed.status_code == 204


async def test_address_history_does_not_duplicate(client, auth_headers):
    device = await client.post(
        "/api/v1/devices", json={"mac_address": "77:88:99:aa:bb:cc"},
        headers=auth_headers,
    )
    device_id = device.json()["id"]

    first = await client.post(
        f"/api/v1/devices/{device_id}/addresses",
        json={"address": "192.168.1.20", "prefix_length": 24, "source": "observed"},
        headers=auth_headers,
    )
    assert first.status_code == 201

    second = await client.post(
        f"/api/v1/devices/{device_id}/addresses",
        json={"address": "192.168.1.20", "source": "configured"},
        headers=auth_headers,
    )
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]  # refreshed, not duplicated
    assert second.json()["source"] == "configured"

    other = await client.post(
        f"/api/v1/devices/{device_id}/addresses",
        json={"address": "10.20.0.5", "prefix_length": 24},
        headers=auth_headers,
    )
    assert other.status_code == 201

    listed = await client.get(f"/api/v1/devices/{device_id}/addresses", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 2


async def test_writes_are_audited(client, auth_headers):
    loc = await client.post(
        "/api/v1/locations", json={"kind": "floor", "name": "Level 2"},
        headers=auth_headers,
    )
    assert loc.status_code == 201

    events = await client.get("/api/v1/audit-events", headers=auth_headers)
    assert events.status_code == 200
    actions = [e["action"] for e in events.json()["items"]]
    assert "location.create" in actions
    assert "auth.login" in actions

    filtered = await client.get(
        "/api/v1/audit-events?action=location.create", headers=auth_headers
    )
    assert filtered.json()["total"] == 1
    event = filtered.json()["items"][0]
    assert event["actor"] == "admin"
    assert event["detail"]["name"] == "Level 2"


async def test_model_delete_blocked_while_assigned(client, auth_headers):
    model = await client.post(
        "/api/v1/device-models", json={"vendor": "D-Link", "model": "DES-1008"},
        headers=auth_headers,
    )
    model_id = model.json()["id"]
    await client.post(
        "/api/v1/devices",
        json={"mac_address": "de:ad:be:ef:00:01", "model_id": model_id},
        headers=auth_headers,
    )

    blocked = await client.delete(f"/api/v1/device-models/{model_id}", headers=auth_headers)
    assert blocked.status_code == 409
