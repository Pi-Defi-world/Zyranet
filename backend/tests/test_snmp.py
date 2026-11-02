"""SNMP/LLDP discovery hardening: parsing, classification, suggestions, structure."""
from __future__ import annotations

from app.services import snmp_discover as snmp


def test_parse_targets_json_and_csv():
    json_raw = (
        '[{"host":"10.0.0.1","community":"private","node_id":"sw-core","port":161},'
        '"10.0.0.2"]'
    )
    targets = snmp._parse_targets(json_raw, default_community="public")
    assert len(targets) == 2
    assert targets[0].node_id == "sw-core"
    assert targets[0].community == "private"
    assert targets[1].community == "public"

    csv_targets = snmp._parse_targets(" 10.0.0.1 , 10.0.0.2 ", default_community="pub")
    assert [t.host for t in csv_targets] == ["10.0.0.1", "10.0.0.2"]
    assert all(t.community == "pub" for t in csv_targets)

    assert snmp._parse_targets("  ") == []


def test_classify_error():
    assert snmp.classify_error("No SNMP response received before timeout") == "timeout"
    assert snmp.classify_error("Unknown SNMP version") == "auth"
    assert snmp.classify_error("No route to host") == "unreachable"
    assert snmp.classify_error("something odd happened") == "error"
    assert snmp.classify_error(None) == "error"


def _doc():
    return {
        "nodes": [
            {"id": "sw-core", "label": "Core Switch", "mgmt_ip": "10.0.0.1"},
            {"id": "sw-acc-1", "label": "Access Switch 1", "mgmt_ip": "10.0.0.2"},
        ],
        "links": [],
    }


def _result(host: str, node_id: str | None, neighbors, ok: bool = True):
    return snmp.DiscoveryResult(
        target=snmp.SnmpTarget(host=host, node_id=node_id),
        ok=ok,
        neighbors=list(neighbors),
    )


def test_suggest_links_dedupes_and_skips_self_links():
    nb = snmp.LldpNeighbor(local_port="1", remote_sys_name="Core Switch", remote_port_desc="23")
    # A node reporting itself (sw-acc-1 seeing "Access Switch 1") must be dropped.
    self_nb = snmp.LldpNeighbor(local_port="2", remote_sys_name="Access Switch 1")
    unknown_nb = snmp.LldpNeighbor(local_port="3", remote_sys_name="ghost-device")

    results = [
        _result("10.0.0.2", None, [nb, nb, self_nb, unknown_nb]),
        _result("10.0.0.2", None, [nb]),  # duplicate target run
        _result("10.0.0.1", "sw-core", [snmp.LldpNeighbor("9", "Access Switch 1")]),
        _result("10.0.0.9", None, [], ok=False),  # failed target ignored
    ]

    links = snmp.suggest_links(_doc(), results)
    keys = [(lk["source"], lk["target"], lk["source_port"]) for lk in links]
    assert keys == [
        ("sw-acc-1", "sw-core", "1"),
        ("sw-core", "sw-acc-1", "9"),
    ]
    assert all(lk["discovered"] for lk in links)


async def test_run_discovery_structured_without_targets():
    out = await snmp.run_discovery("", _doc())
    assert out["ok"] is False
    assert out["error"] == "no_snmp_targets"
    assert out["summary"] == {
        "targets": 0,
        "succeeded": 0,
        "failed": 0,
        "duration_ms": 0.0,
    }


async def test_run_discovery_parallel_with_bounded_concurrency(monkeypatch):
    active = 0
    peak = 0

    def fake_walk(host, community, oid, port=161, *, timeout=2.0, retries=1):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        import time as _t

        _t.sleep(0.05)
        active -= 1
        if host == "10.0.0.9":
            raise RuntimeError("No SNMP response received before timeout")
        return {f"{snmp.LLDP_REM_SYS_NAME}.0.1.1": "sw-core"}

    monkeypatch.setattr(snmp, "_snmp_walk_sync", fake_walk)
    fake_settings = type(
        "S",
        (),
        {
            "snmp_community": "public",
            "snmp_timeout": 1.0,
            "snmp_retries": 0,
            "snmp_max_concurrent": 2,
        },
    )()
    monkeypatch.setattr(snmp, "get_settings", lambda: fake_settings)

    raw = '[{"host":"10.0.0.1"},{"host":"10.0.0.2"},{"host":"10.0.0.3"},{"host":"10.0.0.9"}]'
    out = await snmp.run_discovery(raw, _doc(), max_concurrent=2)

    assert out["ok"] is True  # 3 of 4 targets succeeded
    assert out["summary"]["targets"] == 4
    assert out["summary"]["succeeded"] == 3
    assert out["summary"]["failed"] == 1
    assert out["summary"]["duration_ms"] >= 0
    assert peak <= 2  # bounded concurrency respected

    failed = next(r for r in out["results"] if not r["ok"])
    assert failed["error_class"] == "timeout"
    assert failed["duration_ms"] > 0
    assert all("duration_ms" in r for r in out["results"])
