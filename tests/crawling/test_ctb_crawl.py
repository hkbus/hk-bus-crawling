import pytest

from crawling.ctb_crawl import (
    notify_route_field_warnings,
    route_stop_url,
    routes_url,
    stop_url,
    validate_route_list_fields,
)


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


def test_routes_url():
    assert routes_url() == "https://rt.data.gov.hk/v2/transport/citybus/route/ctb"


def test_stop_url():
    assert (
        stop_url("001234") == "https://rt.data.gov.hk/v2/transport/citybus/stop/001234"
    )


def test_route_stop_url():
    assert (
        route_stop_url("20A", "inbound")
        == "https://rt.data.gov.hk/v2/transport/citybus/route-stop/ctb/20A/inbound"
    )


def test_validate_route_list_fields_all_present_no_warnings():
    route_list = [_route()]

    warnings = validate_route_list_fields(route_list)

    assert warnings == []
    assert route_list[0]["orig_sc"] == "中环 (港澳码头)"
    assert route_list[0]["dest_sc"] == "跑马地 (上)"


def test_validate_route_list_fields_fills_missing_sc_from_tc():
    route_list = [_route(route="796X", orig_sc="", dest_sc=None)]

    warnings = validate_route_list_fields(route_list)

    assert route_list[0]["orig_sc"] == route_list[0]["orig_tc"]
    assert route_list[0]["dest_sc"] == route_list[0]["dest_tc"]
    assert len(warnings) == 2
    assert all("796X" in w for w in warnings)
    assert any("orig_sc" in w for w in warnings)
    assert any("dest_sc" in w for w in warnings)


@pytest.mark.parametrize(
    "missing_field", ["route", "orig_tc", "orig_en", "dest_tc", "dest_en"]
)
def test_validate_route_list_fields_raises_on_other_missing_fields(missing_field):
    overrides = {"route": "796X", missing_field: ""}
    route_list = [_route(**overrides)]

    with pytest.raises(ValueError, match=missing_field):
        validate_route_list_fields(route_list)


def test_validate_route_list_fields_reports_all_broken_routes():
    route_list = [
        _route(route="1", orig_en=""),
        _route(route="2", dest_en=""),
    ]

    with pytest.raises(ValueError) as excinfo:
        validate_route_list_fields(route_list)

    assert "'1'" in str(excinfo.value)
    assert "'2'" in str(excinfo.value)


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        pass


class _FakeAsyncClient:
    def __init__(self, search_result=None):
        self.search_result = search_result or {"items": []}
        self.get_calls = []
        self.post_calls = []

    async def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        return _FakeResponse(self.search_result)

    async def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        return _FakeResponse({"html_url": "https://github.com/o/r/issues/1"})


@pytest.mark.asyncio
async def test_notify_route_field_warnings_noop_without_warnings():
    client = _FakeAsyncClient()

    await notify_route_field_warnings([], client)

    assert client.get_calls == []
    assert client.post_calls == []


@pytest.mark.asyncio
async def test_notify_route_field_warnings_skips_without_github_env(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    client = _FakeAsyncClient()

    await notify_route_field_warnings(["route '796X': 'orig_sc' missing"], client)

    assert client.get_calls == []
    assert client.post_calls == []


@pytest.mark.asyncio
async def test_notify_route_field_warnings_creates_issue_when_none_exists(
    monkeypatch,
):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "open-data-hk/hk-bus-crawling")
    client = _FakeAsyncClient(search_result={"items": []})

    await notify_route_field_warnings(["route '796X': 'orig_sc' missing"], client)

    assert len(client.get_calls) == 1
    assert len(client.post_calls) == 1
    post_url, post_kwargs = client.post_calls[0]
    assert post_url.endswith("/repos/open-data-hk/hk-bus-crawling/issues")
    assert "796X" in post_kwargs["json"]["body"]


@pytest.mark.asyncio
async def test_notify_route_field_warnings_comments_on_existing_issue(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "open-data-hk/hk-bus-crawling")
    client = _FakeAsyncClient(search_result={"items": [{"number": 42}]})

    await notify_route_field_warnings(["route '796X': 'orig_sc' missing"], client)

    post_url, post_kwargs = client.post_calls[0]
    assert post_url.endswith("/issues/42/comments")
    assert "796X" in post_kwargs["json"]["body"]


@pytest.mark.asyncio
async def test_notify_route_field_warnings_never_raises_on_api_failure(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "open-data-hk/hk-bus-crawling")

    class _BoomClient(_FakeAsyncClient):
        async def get(self, url, **kwargs):
            raise RuntimeError("network is down")

    await notify_route_field_warnings(
        ["route '796X': 'orig_sc' missing"], _BoomClient()
    )
