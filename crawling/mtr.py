# -*- coding: utf-8 -*-
# MTR Bus fetching

import asyncio
import csv
import json
from pyproj import Transformer

import logging
import httpx

from crawl_utils import emitRequest

def filterStops(route):
  route['stops'] = [stop for stop in route['stops'] if stop is not None]
  return route

async def getRouteStop(co = 'mtr'):
  a_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, pool=None))
  epsgTransformer = Transformer.from_crs('epsg:2326', 'epsg:4326')

  routeList = {}
  stopList = {}

  r = await emitRequest('https://opendata.mtr.com.hk/data/mtr_lines_and_stations.csv', a_client)
  r.encoding = 'utf-8'
  reader = csv.reader(r.text.split("\n") )
  headers = next(reader,None)
  routes = [route for route in reader if len(route) == 7]
  for [route, bound, stopCode, stopId, chn, eng, seq] in routes:
    if route == "":
      continue
    if route+"_"+bound not in routeList:
      routeList[route+"_"+bound] = {
        "gtfsId": None,
        "route": route,
        "bound": bound,
        "service_type": "1",
        "orig_tc": None,
        "orig_en": None,
        "dest_tc": None,
        "dest_en": None,
        "stops": [None] * 100,
        "fare": []
      }
    if int(float(seq)) == 1:
      routeList[route+"_"+bound]["orig_tc"] = chn
      routeList[route+"_"+bound]["orig_en"] = eng
    routeList[route+"_"+bound]["dest_tc"] = chn
    routeList[route+"_"+bound]["dest_en"] = eng
    routeList[route+"_"+bound]["stops"][int(float(seq))] = stopCode
    if stopCode not in stopList:
      r = await emitRequest('https://geodata.gov.hk/gs/api/v1.0.0/locationSearch?q=港鐵'+chn+"站", a_client, headers={'Accept': 'application/json'})
      lat, lng = epsgTransformer.transform( r.json()[0]['y'], r.json()[0]['x'] )
      stopList[stopCode] = {
        "stop": stopCode,
        "name_en": eng,
        "name_tc": chn,
        "lat": lat,
        "long": lng
      }

  with open('routeList.mtr.json', 'w', encoding='UTF-8') as f:
    f.write(json.dumps(list(map(filterStops, [route for route in routeList.values() if len(route['stops']) > 0])), ensure_ascii=False))
  with open('stopList.mtr.json', 'w', encoding='UTF-8') as f:
    f.write(json.dumps(stopList, ensure_ascii=False))

if __name__=='__main__':
  logging.basicConfig(level=logging.INFO)
  logging.getLogger('httpx').setLevel(logging.WARNING)
  logger = logging.getLogger(__name__)
  asyncio.run(getRouteStop())
