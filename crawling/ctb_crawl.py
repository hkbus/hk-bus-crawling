import argparse
import asyncio
import json
import logging
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
