# -*- coding: utf-8 -*-
# MTR Bus fetching

import asyncio
import csv
import json

import logging
import httpx

from crawl_utils import emitRequest


async def getRouteStop(co='lrtfeeder'):
  a_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, pool=None))
  routeList = {}
  stopList = {}

  r = await emitRequest('https://opendata.mtr.com.hk/data/mtr_bus_routes.csv', a_client)
  r.encoding = 'utf-8'
  reader = csv.reader(r.text.split("\n"))
  headers = next(reader, None)
  routes = [route for route in reader if len(route) >= 4]
  for [route, chn, eng, *rest] in routes:
    if route == '':
      continue
    start = {
        "zh": chn.split('至')[0],
        "en": eng.split(' to ')[0]
    }
    end = {
        "zh": chn.split('至')[1],
        "en": eng.split(' to ')[1]
    }
    for bound in ['I', 'O']:
      routeList[route + "_" + bound] = {
          "route": route,
          "bound": bound,
          "service_type": "1",
          "orig_tc": start['zh'] if bound == 'O' else end['zh'],
          "dest_tc": end["zh"] if bound == 'O' else start['zh'],
          "orig_en": start['en'] if bound == 'O' else end['en'],
          "dest_en": end["en"] if bound == 'O' else start['en'],
          "stops": [],
          "co": "lrtfeeder"
      }

  # Parse stops
  r = await emitRequest('https://opendata.mtr.com.hk/data/mtr_bus_stops.csv', a_client)
  r.encoding = 'utf-8'
  reader = csv.reader(r.text.split("\n"))
  headers = next(reader, None)
  stops = [stop for stop in reader if len(stop) >= 8]
  for [
      route,
      bound,
      seq,
      stationId,
      lat,
      lng,
      name_zh,
      name_en,
          *rest] in stops:
    routeKey = route + "_" + bound
    if routeKey in routeList:
      routeList[routeKey]['stops'].append(stationId)
    else:
      print("error", routeKey)
    stopList[stationId] = {
        "stop": stationId,
        "name_en": name_en,
        "name_tc": name_zh,
        "lat": lat,
        "long": lng
    }

  with open('routeList.lrtfeeder.json', 'w', encoding='UTF-8') as f:
    f.write(json.dumps([route for route in routeList.values()
            if len(route['stops']) > 0], ensure_ascii=False))
  with open('stopList.lrtfeeder.json', 'w', encoding='UTF-8') as f:
    f.write(json.dumps(stopList, ensure_ascii=False))

if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  logging.getLogger('httpx').setLevel(logging.WARNING)
  logger = logging.getLogger(__name__)
  asyncio.run(getRouteStop())
