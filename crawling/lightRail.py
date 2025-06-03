# -*- coding: utf-8 -*-
# MTR Bus fetching

import asyncio
import csv
import json
from pyproj import Transformer
import logging
import httpx

from crawl_utils import emitRequest

# List of Circular Routes 
circularRoutes = ["705", "706"]

def getbound(route, bound):
  if route in circularRoutes:
    return "O"
  else:
    return "O" if bound == "1" else "I"
  
def routeKey(route, bound):
    if route in circularRoutes:
        return f"{route}_O"
    return f"{route}_{bound}"

async def getRouteStop(co='lightRail'):
  a_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, pool=None))

  epsgTransformer = Transformer.from_crs('epsg:2326', 'epsg:4326')

  routeList = {}
  stopList = {}
  orig_set = set()

  r = await emitRequest('https://opendata.mtr.com.hk/data/light_rail_routes_and_stops.csv', a_client)
  reader = csv.reader(r.text.split("\n"))
  headers = next(reader, None)
  routes = [route for route in reader if len(route) == 7]
  for [route, bound, stopCode, stopId, chn, eng, seq] in routes:
    key = routeKey(route, bound)
    if key not in routeList:
      routeList[key] = {
          "gtfsId": None,
          "route": route,
          "bound": getbound(route, bound),
          "service_type": "1",
          "orig_tc": None,
          "orig_en": None,
          "dest_tc": None,
          "dest_en": None,
          "stops": [],
          "fare": []
      }
    if key not in orig_set:
      routeList[key]["orig_tc"] = chn
      routeList[key]["orig_en"] = eng
      orig_set.add(key)
    routeList[key]["dest_tc"] = chn
    routeList[key]["dest_en"] = eng
    if not routeList[key]["stops"] or routeList[key]["stops"][-1] != "LR" + stopId:
      if route in circularRoutes and seq != "1.00":
        # Avoid adding the same stop (orig & dest) twice in circular routes
        if "LR" + stopId == routeList[key]["stops"][0]:
          continue
      routeList[key]["stops"].append("LR" + stopId)
    if "LR" + stopId not in stopList:
      url = f'https://geodata.gov.hk/gs/api/v1.0.0/locationSearch?q={chn}輕鐵站'
      r = await emitRequest(url, a_client, headers={'Accept': 'application/json'})
      try:
        lat, lng = epsgTransformer.transform(
            r.json()[0]['y'], r.json()[0]['x'])
        stopList["LR" + stopId] = {
            "stop": "LR" + stopId,
            "name_en": eng,
            "name_tc": chn,
            "lat": lat,
            "long": lng
        }
      except BaseException:
        logger.exception(f"Error parsing {url}: {r.text}")
        raise

  with open('routeList.lightRail.json', 'w', encoding='UTF-8') as f:
    f.write(json.dumps([route for route in routeList.values()
            if len(route['stops']) > 0], ensure_ascii=False))
  with open('stopList.lightRail.json', 'w', encoding='UTF-8') as f:
    f.write(json.dumps(stopList, ensure_ascii=False))

if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  logging.getLogger('httpx').setLevel(logging.WARNING)
  logger = logging.getLogger(__name__)
  asyncio.run(getRouteStop())
