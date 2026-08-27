import json

import pytest

import crawling.ctb as ctb


def _route(**overrides):
    route = {
        "co": "CTB",
        "route": "1",
        "orig_tc": "中環 (港澳碼頭)",
        "orig_en": "Central (Macao Ferry)",
        "orig_sc": "中环 (港澳码头)",
        "dest_tc": "跑馬地 (上)",
        "dest_en": "Happy Valley (Upper)",
        "dest_sc": "跑马地 (上)",
        "data_timestamp": "2026-08-27T05:00:02+08:00",
    }
    route.update(overrides)
    return route


@pytest.fixture
def raw_ctb_files(tmp_path, monkeypatch):
    """Point crawling.ctb's raw file constants at a scratch dir."""
    route_list_path = tmp_path / "ctb.raw.routeList.json"
    route_stop_list_path = tmp_path / "ctb.raw.routeStopList.json"
    stop_list_path = tmp_path / "ctb.raw.stopList.json"

    monkeypatch.setattr(ctb, "RAW_ROUTE_LIST", route_list_path)
    monkeypatch.setattr(ctb, "RAW_ROUTE_STOP_LIST", route_stop_list_path)
    monkeypatch.setattr(ctb, "RAW_STOP_LIST", stop_list_path)
    monkeypatch.setattr(ctb, "dump_provider_data", lambda *a, **k: None)

    return route_list_path, route_stop_list_path, stop_list_path


@pytest.mark.asyncio
async def test_prepare_data_fills_missing_sc_from_stale_raw_file(
    raw_ctb_files, monkeypatch
):
    """Reproduces the fetch-data.yml path: a stale/S3-downloaded raw file is
    already on disk (ctb_crawl.py never re-validates it), so ctb.py's own
    load must repair it instead of KeyError-ing on route["dest_sc"].
    """
    route_list_path, route_stop_list_path, stop_list_path = raw_ctb_files

    route_list_path.write_text(
        json.dumps([_route(route="796X", orig_sc="", dest_sc=None)]),
        encoding="UTF-8",
    )
    route_stop_list_path.write_text(
        json.dumps(
            {
                "796X-inbound": [{"stop": "001"}],
                "796X-outbound": [{"stop": "002"}],
            }
        ),
        encoding="UTF-8",
    )
    stop_list_path.write_text(
        json.dumps([{"stop": "001", "long": 0}, {"stop": "002", "long": 0}]),
        encoding="UTF-8",
    )

    notified = []

    async def fake_notify(warnings, a_client):
        notified.append(warnings)

    monkeypatch.setattr(ctb, "notify_route_field_warnings", fake_notify)

    await ctb.prepare_data()

    assert len(notified) == 1
    assert any("796X" in w for w in notified[0])

    persisted = json.loads(route_list_path.read_text("utf-8"))
    assert persisted[0]["orig_sc"] == persisted[0]["orig_tc"]
    assert persisted[0]["dest_sc"] == persisted[0]["dest_tc"]


@pytest.mark.asyncio
async def test_prepare_data_raises_on_other_missing_fields(raw_ctb_files, monkeypatch):
    route_list_path, route_stop_list_path, stop_list_path = raw_ctb_files

    route_list_path.write_text(
        json.dumps([_route(route="796X", dest_en="")]), encoding="UTF-8"
    )
    route_stop_list_path.write_text(json.dumps({}), encoding="UTF-8")
    stop_list_path.write_text(json.dumps([]), encoding="UTF-8")

    with pytest.raises(ValueError, match="796X"):
        await ctb.prepare_data()
