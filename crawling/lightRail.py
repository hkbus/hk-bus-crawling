# -*- coding: utf-8 -*-
# MTR Bus fetching (merged sources)

import asyncio
import csv
import json
from pyproj import Transformer
import logging
import httpx
from typing import List

from crawl_utils import emitRequest

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


async def fetch_csv_text(url: str, client: httpx.AsyncClient, retries: int = 2) -> str:
  for attempt in range(retries + 1):
    try:
      r = await emitRequest(url, client)
      return r.text
    except Exception as e:
      logging.getLogger(__name__).warning(
          "Failed to fetch %s (attempt %d): %s", url, attempt + 1, e)
      if attempt == retries:
        raise
      await asyncio.sleep(1)
  raise RuntimeError("unreachable")


async def getRouteStop(co='lightRail'):
  a_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, pool=None))

  epsgTransformer = Transformer.from_crs('epsg:2326', 'epsg:4326')

  routeList = {}
  stopList = {}
  routeCollection = set()

  csv_urls = [
      'https://opendata.mtr.com.hk/data/light_rail_routes_and_stops.csv',
      'https://notice.hkbus.app/handmade_data/lightRail/506P*.csv',
      'https://notice.hkbus.app/handmade_data/lightRail/507P*.csv',
      'https://notice.hkbus.app/handmade_data/lightRail/720*.csv',
      'https://notice.hkbus.app/handmade_data/lightRail/751*.csv',
      'https://notice.hkbus.app/handmade_data/lightRail/751P.csv',
      'https://notice.hkbus.app/handmade_data/lightRail/SPR.csv'
  ]

  for url in csv_urls:
    try:
      text = await fetch_csv_text(url, a_client)
    except Exception:
      logging.getLogger(__name__).warning(
          "Skipping CSV source after repeated failures: %s", url)
      continue

    reader = csv.reader(text.splitlines())
    headers = next(reader, None)
    # Only process rows with expected minimum columns
    routes = [route for route in reader if len(route) >= 7]

    for [route, bound, stopCode, stopId, chn, eng, seq, *rest] in routes:
      key = routeKey(route, bound)
      lightRailId = "LR" + stopId
      if key not in routeList:
        lightRailObject = routeList[key] = {
            "gtfsId": None,
            "route": route,
            "bound": getBound(route, bound),
            "service_type": "1",
            "orig_tc": None,
            "orig_en": None,
            "dest_tc": None,
            "dest_en": None,
            "stops": [],
            "fare": []
        }
      else:
        lightRailObject = routeList[key]

      if key not in routeCollection:
        lightRailObject["orig_tc"] = chn
        lightRailObject["orig_en"] = eng
        routeCollection.add(key)
      lightRailObject["dest_tc"] = chn + \
          " (循環線)" if route in circularRoutes else chn
      lightRailObject["dest_en"] = eng + \
          " (Circular)" if route in circularRoutes else eng
      if not lightRailObject["stops"] or lightRailObject["stops"][-1] != lightRailId:
        if route in circularRoutes and seq != "1.00":
          # Avoid adding the same stop (orig & dest) twice in circular routes
          if lightRailObject["stops"] and lightRailId == lightRailObject["stops"][0]:
            continue
        lightRailObject["stops"].append(lightRailId)

      if lightRailId not in stopList:
        lookup_url = f'https://www.map.gov.hk/gs/api/v1.0.0/locationSearch?q={chn}輕鐵站'
        try:
          r = await emitRequest(lookup_url, a_client, headers={'Accept': 'application/json',
                                                               'User-Agent': ''})
          j = r.json()
          if not j:
            raise ValueError("empty result")
          lat, lng = epsgTransformer.transform(j[0]['y'], j[0]['x'])
          stopList[lightRailId] = {
              "stop": lightRailId,
              "name_en": eng,
              "name_tc": chn,
              "lat": lat,
              "long": lng
          }
        except Exception:
          logging.getLogger(__name__).exception(
              "Error parsing or geocoding %s: %s", lookup_url, getattr(
                  r, "text", ""))
          # continue without raising; some stops may be missing geo info

  # Write outputs
  with open('routeList.lightRail.json', 'w', encoding='UTF-8') as f:
    f.write(json.dumps([route for route in routeList.values()
            if len(route['stops']) > 0], ensure_ascii=False))
  with open('stopList.lightRail.json', 'w', encoding='UTF-8') as f:
    f.write(json.dumps(stopList, ensure_ascii=False))

  await a_client.aclose()


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  logging.getLogger('httpx').setLevel(logging.WARNING)
  logger = logging.getLogger(__name__)
  asyncio.run(getRouteStop())
