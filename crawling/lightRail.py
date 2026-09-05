# -*- coding: utf-8 -*-
# MTR Bus fetching

import asyncio
import csv
import logging

import httpx
from crawl_utils import dump_provider_data, emitRequest
from schemas import ProviderRoute, ProviderStop
from utils import DATA_DIR, query_igeocom_geojson

BASE_URL = "https://opendata.mtr.com.hk/data"


def routes_stops_url():
    return BASE_URL + "/light_rail_routes_and_stops.csv"


# List of Circular Routes
circularRoutes = ("705", "706")


def getBound(route, bound):
    if route in circularRoutes:
        return "O"
    else:
        return "O" if bound == "1" else "I"


def routeKey(route, bound):
    if route in circularRoutes:
        return f"{route}_O"
    return f"{route}_{bound}"


async def getRouteStop(co="lightRail"):
    if (DATA_DIR / f"routeList.{co}.json").exists() and (
        DATA_DIR / f"stopList.{co}.json"
    ).exists():
        return
    a_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, pool=None))

    routeList = {}
    stopList: dict[str, ProviderStop] = {}
    routeCollection = set()

    igeocom_features = query_igeocom_geojson(class_code="TRS", type_code="LRA")
    stations = {}

    for feature in igeocom_features:
        raw_chi_name = feature["properties"]["CHINESENAME"]
        chi_name = raw_chi_name.replace("輕鐵－", "")
        stations[chi_name] = feature

    r = await emitRequest(routes_stops_url(), a_client)
    reader = csv.reader(r.text.split("\n"))
    headers = next(reader, None)
    routes = [route for route in reader if len(route) >= 7]
    for [route, bound, stopCode, stopId, chn, eng, seq, *rest] in routes:
        key = routeKey(route, bound)
        lightRailId = "LR" + stopId
        if key not in routeList:
            lightRailObject = routeList[key] = {
                "co": co,
                "route": route,
                "bound": getBound(route, bound),
                "service_type": "1",
                "orig_tc": None,
                "orig_sc": None,
                "orig_en": None,
                "dest_tc": None,
                "dest_sc": None,
                "dest_en": None,
                "stops": [],
                "fare": [],
            }
        else:
            lightRailObject = routeList[key]

        if key not in routeCollection:
            lightRailObject["orig_tc"] = chn
            lightRailObject["orig_sc"] = chn
            lightRailObject["orig_en"] = eng
            routeCollection.add(key)
        lightRailObject["dest_tc"] = (
            chn + " (循環線)" if route in circularRoutes else chn
        )
        lightRailObject["dest_sc"] = lightRailObject["dest_tc"]
        lightRailObject["dest_en"] = (
            eng + " (Circular)" if route in circularRoutes else eng
        )
        if not lightRailObject["stops"] or lightRailObject["stops"][-1] != lightRailId:
            if route in circularRoutes and seq != "1":
                # Avoid adding the same stop (orig & dest) twice in circular routes
                if lightRailId == lightRailObject["stops"][0]:
                    continue
            lightRailObject["stops"].append(lightRailId)

        if lightRailId not in stopList:

            feature = stations[chn]

            lng, lat = feature["geometry"]["coordinates"]
            stopList[lightRailId] = {
                "stop": lightRailId,
                "name_en": eng,
                "name_tc": chn,
                "name_sc": chn,
                "lat": lat,
                "lng": lng,
            }

    routes: list[ProviderRoute] = [
        route for route in routeList.values() if len(route["stops"]) > 0
    ]
    dump_provider_data(co, routes, stopList)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logger = logging.getLogger(__name__)
    asyncio.run(getRouteStop())
