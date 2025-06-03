# -*- coding: utf-8 -*-
# MTR Bus fetching

import asyncio
import csv
import json
from pyproj import Transformer
import logging
import httpx

from crawl_utils import emitRequest


async def getRouteStop(co='lightRail'):
  a_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, pool=None))

  epsgTransformer = Transformer.from_crs('epsg:2326', 'epsg:4326')

  routeList = {}
  stopList = {}

  r = await emitRequest('https://opendata.mtr.com.hk/data/light_rail_routes_and_stops.csv', a_client)
  reader = csv.reader(r.text.split("\n"))
  headers = next(reader, None)
  routes = [route for route in reader if len(route) == 7]
  for [route, bound, stopCode, stopId, chn, eng, seq] in routes:
    if route + "_" + bound not in routeList:
      routeList[route + "_" + bound] = {
          "gtfsId": None,
          "route": route,
          "bound": "O" if bound == "1" else "I",
          "service_type": "1",
          "orig_tc": None,
          "orig_en": None,
          "dest_tc": None,
          "dest_en": None,
          "stops": [],
          "fare": []
      }
    if seq == "1.00":
      routeList[route + "_" + bound]["orig_tc"] = chn
      routeList[route + "_" + bound]["orig_en"] = eng
    routeList[route + "_" + bound]["dest_tc"] = chn
    routeList[route + "_" + bound]["dest_en"] = eng
    routeList[route + "_" + bound]["stops"].append("LR" + stopId)
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
