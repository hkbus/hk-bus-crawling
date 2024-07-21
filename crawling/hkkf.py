# -*- coding: utf-8 -*-
import asyncio
import logging

import httpx

import json
import time

from crawl_utils import emitRequest

routes = {
 "1": ["Central Pier 4", "Sok Kwu Wan"],
 "2": ["Central Pier 4", "Yung Shue Wan"],
 "3": ["Central Pier 6", "Peng Chau"],
 "4": ["Peng Chau", "Hei Ling Chau"],
}

def parseStop(name_en, apiStops):
  for stop in apiStops:
    if stop["name_en"].startswith(name_en):
      return stop
  raise Exception("Undefined stop")

async def getRouteStop(co):
  a_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, pool=None))
  routeList = []
  stopList = {}

  r = await emitRequest('https://www.hkkfeta.com/opendata/route/', a_client)
  apiRoutes = r.json()['data']
  apiStops = []
  for stopId in [1,2,3,4,5,6]:
    stop = (await emitRequest('https://www.hkkfeta.com/opendata/pier/'+str(stopId), a_client)).json()["data"]
    apiStops.append(stop)


  with open("gtfs.json", 'r', encoding="utf-8") as f:
    gtfsZh = json.load(f)

  with open("gtfs-en.json", 'r', encoding="utf-8") as f:
    gtfs = json.load(f)
    gtfsRoutes = gtfs["routeList"]
    gtfsStops = gtfs["stopList"]

  for apiRoute in apiRoutes:
    orig = parseStop(routes[str(apiRoute["route_id"])][0], apiStops)
    dest = parseStop(routes[str(apiRoute["route_id"])][1], apiStops)
    routeList.append({
      "route": "KF" + str(apiRoute["route_id"]),
      "orig_tc": orig["name_tc"],
      "orig_en": orig["name_en"],
      "dest_tc": dest["name_tc"],
      "dest_en": dest["name_en"],
      "service_type": 1,
      "bound": "O",
      "stops": [
        "KF" + str(orig["pier_id"]),
        "KF" + str(dest["pier_id"]),
      ]
    })
    routeList.append({
      "route": "KF" + str(apiRoute["route_id"]),
      "orig_tc": dest["name_tc"],
      "orig_en": dest["name_en"],
      "dest_tc": orig["name_tc"],
      "dest_en": orig["name_en"],
      "service_type": 1,
      "bound": "I",
      "stops": [
        "KF" + str(dest["pier_id"]),
        "KF" + str(orig["pier_id"]),
      ]
    })

  for apiStop in apiStops:
    stopList["KF"+str(apiStop["pier_id"])] = {
      "stop": "KF"+str(apiStop["pier_id"]),
      "name_en": apiStop["name_en"],
      "name_tc": apiStop["name_tc"],
      "lat": apiStop["lat"],
      "long": apiStop["long"]
    }

  with open('routeList.hkkf.json', 'w', encoding="utf-8") as f:
    f.write(json.dumps(routeList, ensure_ascii=False))

  with open('stopList.hkkf.json', 'w', encoding="utf-8") as f:
    f.write(json.dumps(stopList, ensure_ascii=False))

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    asyncio.run(getRouteStop('hkkf'))
