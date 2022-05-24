# -*- coding: utf-8 -*-
# MTR Bus fetching

import csv
import requests
import json
from pyproj import Transformer

epsgTransformer = Transformer.from_crs('epsg:2326', 'epsg:4326')

routeList = {}
stopList = {}

r = requests.get('https://opendata.mtr.com.hk/data/mtr_lines_and_stations.csv')
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
  if seq == "1":
    routeList[route+"_"+bound]["orig_tc"] = chn
    routeList[route+"_"+bound]["orig_en"] = eng
  routeList[route+"_"+bound]["dest_tc"] = chn
  routeList[route+"_"+bound]["dest_en"] = eng
  routeList[route+"_"+bound]["stops"][int(float(seq))] = stopCode
  if stopCode not in stopList:
    r = requests.get('https://geodata.gov.hk/gs/api/v1.0.0/locationSearch?q=港鐵'+chn+"站", headers={'Accept': 'application/json'})
    lat, lng = epsgTransformer.transform( r.json()[0]['y'], r.json()[0]['x'] )
    stopList[stopCode] = {
      "stop": stopCode,
      "name_en": eng,
      "name_tc": chn,
      "lat": lat,
      "long": lng
    }

def filterStops(route):
  route['stops'] = [stop for stop in route['stops'] if stop is not None]
  return route

with open('routeList.mtr.json', 'w') as f:
  f.write(json.dumps(list(map(filterStops, [route for route in routeList.values() if len(route['stops']) > 0])), ensure_ascii=False))
with open('stopList.mtr.json', 'w') as f:
  f.write(json.dumps(stopList, ensure_ascii=False))