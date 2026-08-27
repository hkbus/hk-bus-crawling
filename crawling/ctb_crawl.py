import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Literal

import httpx

try:
    from .crawl_utils import emitRequest, get_request_limit
    from .utils import DATA_DIR
except ImportError:
    from crawl_utils import emitRequest, get_request_limit
    from utils import DATA_DIR

logger = logging.getLogger(__name__)

# Raw list files
RAW_ROUTE_LIST = DATA_DIR / ("ctb.raw.routeList.json")
RAW_ROUTE_STOP_LIST = DATA_DIR / ("ctb.raw.routeStopList.json")
RAW_STOP_LIST = DATA_DIR / ("ctb.raw.stopList.json")

BASE_URL = "https://rt.data.gov.hk/v2/transport/citybus"

# Fields every raw ctb route entry must have; missing any of these is a fatal
# data error that fails the pipeline.
HARD_REQUIRED_ROUTE_FIELDS = ("route", "orig_tc", "orig_en", "dest_tc", "dest_en")
# orig_sc/dest_sc are allowed to be missing (the upstream API has dropped them
# before, e.g. #78): fall back to the tc counterpart and just warn instead.
SC_FALLBACK_FIELDS = {"orig_sc": "orig_tc", "dest_sc": "dest_tc"}

GITHUB_API_URL = "https://api.github.com"
DATA_ISSUE_LABEL = "ctb-data-quality"
DATA_ISSUE_TITLE = "[ctb_crawl] Route missing orig_sc/dest_sc fields"


def routes_url():
    return BASE_URL + "/route/ctb"


def stop_url(stopId: str):
    return BASE_URL + "/stop/" + stopId


def route_stop_url(route: str, direction: Literal["inbound", "outbound"]):
    return BASE_URL + "/route-stop/ctb/" + route + "/" + direction


req_route_stop_limit = asyncio.Semaphore(get_request_limit())
req_stop_list_limit = asyncio.Semaphore(get_request_limit())

# methods of single API request


async def get_route_list(a_client) -> list[dict]:
    logger.info("Fetching route list of ctb")
    r = await emitRequest(routes_url(), a_client)
    return r.json()["data"]


async def get_stop(stopId, a_client) -> dict:
    async with req_stop_list_limit:
        r = await emitRequest(stop_url(stopId), a_client)
    return r.json()["data"]


async def get_route_stop(route: str, a_client) -> dict[str, list[dict]]:
    # TODO: remove this commented code if found useless
    # if route.get("bound", 0) != 0 or route.get("stops", {}):
    #     return route

    route_stops = {}
    for direction in ["inbound", "outbound"]:
        async with req_route_stop_limit:
            r = await emitRequest(
                route_stop_url(route, direction),
                a_client,
            )
        result = r.json()["data"]
        route_key = f"{route}-{direction}"

        route_stops[route_key] = result
    return route_stops


# data quality check + notification


def validate_route_list_fields(route_list: list[dict]) -> list[str]:
    """Validate required fields on every raw ctb route.

    orig_sc/dest_sc missing on a route is repaired in place (the route dict is
    mutated) by copying the tc counterpart, and recorded as a warning string
    returned to the caller so it can be reported without failing the pipeline.

    Any other required field missing is a fatal data error: these are
    collected across all routes and raised together, so the pipeline fails
    with the full list of broken routes rather than just the first one found.
    """
    errors = []
    warnings = []

    for route in route_list:
        route_id = route.get("route", "<unknown>")

        missing_hard = [f for f in HARD_REQUIRED_ROUTE_FIELDS if not route.get(f)]
        if missing_hard:
            errors.append(
                f"route {route_id!r} missing field(s): {', '.join(missing_hard)}"
            )
            continue

        for sc_field, tc_field in SC_FALLBACK_FIELDS.items():
            if not route.get(sc_field):
                route[sc_field] = route[tc_field]
                warnings.append(
                    f"route {route_id!r}: {sc_field!r} missing, filled from "
                    f"{tc_field!r} ({route[tc_field]!r})"
                )

    if errors:
        raise ValueError(
            "CTB route list has route(s) missing required field(s):\n"
            + "\n".join(errors)
        )

    return warnings


async def notify_route_field_warnings(
    warnings: list[str], a_client: httpx.AsyncClient
) -> None:
    """Best-effort notification about repaired-but-broken route data.

    Files (or comments on) a GitHub issue so a data owner can fix the
    upstream API. This must never raise: a notification failure should not
    fail the crawl pipeline, so every failure mode here is caught and logged.
    """
    if not warnings:
        return

    body = (
        "Automated check in `crawling/ctb_crawl.py` found CTB route(s) missing "
        "`orig_sc`/`dest_sc`. The Traditional Chinese value was substituted so "
        "the pipeline could keep running, but the upstream CTB API data should "
        "still be fixed:\n\n" + "\n".join(f"- {w}" for w in warnings)
    )

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        logger.error(
            "CTB route field warning(s) (GITHUB_TOKEN/GITHUB_REPOSITORY not set, "
            "skipping GitHub issue notification):\n%s",
            body,
        )
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    try:
        search_query = (
            f'repo:{repo} type:issue state:open label:"{DATA_ISSUE_LABEL}" '
            f'in:title "{DATA_ISSUE_TITLE}"'
        )
        r = await a_client.get(
            f"{GITHUB_API_URL}/search/issues",
            headers=headers,
            params={"q": search_query},
        )
        r.raise_for_status()
        existing_issues = r.json().get("items", [])

        if existing_issues:
            issue_number = existing_issues[0]["number"]
            r = await a_client.post(
                f"{GITHUB_API_URL}/repos/{repo}/issues/{issue_number}/comments",
                headers=headers,
                json={"body": body},
            )
            r.raise_for_status()
            logger.warning(
                "Added CTB route field warning(s) to existing issue #%s",
                issue_number,
            )
        else:
            r = await a_client.post(
                f"{GITHUB_API_URL}/repos/{repo}/issues",
                headers=headers,
                json={
                    "title": DATA_ISSUE_TITLE,
                    "body": body,
                    "labels": [DATA_ISSUE_LABEL],
                },
            )
            r.raise_for_status()
            logger.warning(
                "Filed issue %s for CTB route field warning(s)",
                r.json().get("html_url"),
            )
    except Exception:
        logger.exception(
            "Failed to notify data owner about CTB route field warning(s):\n%s",
            body,
        )


# methods of multiple API requests


async def get_stop_list(stops, a_client) -> list[dict]:
    logger.info("Fetching stop list of ctb")
    ret = await asyncio.gather(*[get_stop(stop, a_client) for stop in stops])
    return ret


async def get_route_stop_list(route_list: list[dict], a_client) -> dict[str, list]:
    logger.info("Fetching route stop list of ctb")
    route_stop_list = await asyncio.gather(
        *[get_route_stop(route["route"], a_client) for route in route_list]
    )

    route_stops = {}
    for single_route_stops in route_stop_list:
        for route_key, route_stop in single_route_stops.items():
            route_stops[route_key] = route_stop

    return route_stops


async def prepare_raw_data(force: bool = False):
    if (
        not force
        and RAW_ROUTE_LIST.exists()
        and RAW_ROUTE_STOP_LIST.exists()
        and RAW_STOP_LIST.exists()
    ):
        logger.info("Raw data of ctb already exists, skipping...")
        return

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, pool=None)) as a_client:
        raw_route_list_path = Path(RAW_ROUTE_LIST)
        if raw_route_list_path.exists() and not force:
            route_list = json.loads(raw_route_list_path.read_text("utf-8"))
        else:
            route_list = await get_route_list(a_client)
            field_warnings = validate_route_list_fields(route_list)
            if field_warnings:
                await notify_route_field_warnings(field_warnings, a_client)
            raw_route_list_path.write_text(
                json.dumps(route_list, ensure_ascii=False), encoding="UTF-8"
            )

        raw_route_stop_list_path = Path(RAW_ROUTE_STOP_LIST)
        if raw_route_stop_list_path.exists() and not force:
            route_stop_list = json.loads(raw_route_stop_list_path.read_text("utf-8"))
        else:
            route_stop_list = await get_route_stop_list(route_list, a_client)
            raw_route_stop_list_path.write_text(
                json.dumps(route_stop_list, ensure_ascii=False), encoding="UTF-8"
            )

        _stop_ids = []
        for route in route_list:
            for direction in ["inbound", "outbound"]:
                route_code = f"{route['route']}-{direction}"
                route_stop = route_stop_list[route_code]
                _stop_ids.extend([stop["stop"] for stop in route_stop])

        _stop_ids = sorted(set(_stop_ids))
        raw_stop_list_path = Path(RAW_STOP_LIST)
        if raw_stop_list_path.exists() and not force:
            return

        stop_list_raw = await get_stop_list(_stop_ids, a_client)
        raw_stop_list_path.write_text(
            json.dumps(stop_list_raw, ensure_ascii=False), encoding="UTF-8"
        )


def parse_args():
    parser = argparse.ArgumentParser(description="Crawl raw CTB data files")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Fetch raw data again even when local raw files already exist",
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    args = parse_args()
    asyncio.run(prepare_raw_data(force=args.force))
