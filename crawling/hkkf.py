# -*- coding: utf-8 -*-

import requests
import json
import time

routes = {
 "1": ["Central Pier 4", "Sok Kwu Wan"],
 "2": ["Central Pier 4", "Yung Shue Wan"],
 "3": ["Central Pier 6", "Peng Chau"],
 "4": ["Peng Chau", "Hei Ling Chau"],
}

def emitRequest(url):
  # retry if "Too many request (429)"
  while True:
    r = requests.get(url)
    if r.status_code == 200:
      return r
    elif r.status_code == 429:
      time.sleep(1)
    else:
      raise Exception(r.status_code, url)

routeList = []
stopList = {}

r = emitRequest('https://www.hkkfeta.com/opendata/route/')
apiRoutes = r.json()['data']
apiStops = []
for stopId in [1,2,3,4,5,6]:
  stop = emitRequest('https://www.hkkfeta.com/opendata/pier/'+str(stopId)).json()["data"]
  apiStops.append(stop)


with open("gtfs.json") as f:
  gtfsZh = json.load(f)

with open("gtfs-en.json") as f:
  gtfs = json.load(f)
  gtfsRoutes = gtfs["routeList"]
  gtfsStops = gtfs["stopList"]

def parseStop(name_en):
  for stop in apiStops: 
    if stop["name_en"].startswith(name_en):
      return stop
  raise Exception("Undefined stop")

for apiRoute in apiRoutes:
  orig = parseStop(routes[str(apiRoute["route_id"])][0])
  dest = parseStop(routes[str(apiRoute["route_id"])][1])
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

with open('routeList.hkkf.json', 'w') as f:
  f.write(json.dumps(routeList, ensure_ascii=False))

with open('stopList.hkkf.json', 'w') as f:
  f.write(json.dumps(stopList, ensure_ascii=False))