# -*- coding: utf-8 -*-

import json

with open("gtfs.json", 'r', encoding="utf-8") as f:
  gtfsZh = json.load(f)

with open("gtfs-en.json", 'r', encoding="utf-8") as f:
  gtfs = json.load(f)
  gtfsRoutes = gtfs["routeList"]
  gtfsStops = gtfs["stopList"]

routes = {
    "CECC": ["Central", "Cheung Chau"],
    "CCCE": ["Cheung Chau", "Central"],
    "CEMW": ["Central", "Mui Wo"],
    "MWCE": ["Mui Wo", "Central"],
    "NPHH": ["North Point", "Hung Hom"],
    "HHNP": ["Hung Hom", "North Point"],
    "NPKC": ["North Point", "Kowloon City"],
    "KCNP": ["Kowloon City", "North Point"],
    "IIPECMUW": ["Peng Chau", "Mui Wo"],
    "IIMUWPEC": ["Mui Wo", "Peng Chau"],
    "IIMUWCMW": ["Mui Wo", "Chi Ma Wan"],
    "IICMWMUW": ["Chi Ma Wan", "Mui Wo"],
    "IICMWCHC": ["Chi Ma Wan", "Cheung Chau"],
    "IICHCCMW": ["Cheung Chau", "Chi Ma Wan"],
    "IICHCMUW": ["Cheung Chau", "Mui Wo"],
    "IIMUWCHC": ["Mui Wo", "Cheung Chau "],
}

routeList = []
stopList = {}

for [route_code, [orig, dest]] in routes.items():
  for route_id, gtfsRoute in gtfsRoutes.items():
    if "ferry" in gtfsRoute["co"]:
      if orig.lower() == gtfsRoute["orig"]["en"].lower(
      ) and dest.lower() == gtfsRoute["dest"]["en"].lower():
        routeList.append({
            "gtfsId": route_id,
            "route": route_code,
            "orig_tc": gtfsZh["routeList"][route_id]["orig"]["zh"],
            "orig_en": gtfsRoute["orig"]["en"],
            "dest_tc": gtfsZh["routeList"][route_id]["dest"]["zh"],
            "dest_en": gtfsRoute["dest"]["en"],
            "service_type": 1,
            "bound": "O",
            "stops": gtfsRoute["stops"]["1"],
            "freq": gtfsRoute["freq"]["1"],
        })
      elif dest.lower() == gtfsRoute["orig"]["en"].lower() and orig.lower() == gtfsRoute["dest"]["en"].lower():
        routeList.append({
            "gtfsId": route_id,
            "route": route_code,
            "dest_tc": gtfsZh["routeList"][route_id]["orig"]["zh"],
            "dest_en": gtfsRoute["orig"]["en"],
            "orig_tc": gtfsZh["routeList"][route_id]["dest"]["zh"],
            "orig_en": gtfsRoute["dest"]["en"],
            "service_type": 1,
            "bound": "I",
            "stops": gtfsRoute["stops"]["2"] if "2" in gtfsRoute["stops"] else gtfsRoute["stops"]["1"][::-1],
            "freq": gtfsRoute["freq"]["2"] if "2" in gtfsRoute["freq"] else {},
        })


for route in routeList:
  for stopId in route["stops"]:
    stopList[stopId] = {
        "stop": stopId,
        "name_en": gtfsStops[stopId]["stopName"]["unknown"],
        "name_tc": gtfsZh["stopList"][stopId]["stopName"]["unknown"],
        "lat": gtfsStops[stopId]["lat"],
        "long": gtfsStops[stopId]["lng"],
    }

with open('routeList.sunferry.json', 'w', encoding='UTF-8') as f:
  f.write(json.dumps(routeList, ensure_ascii=False))


with open('stopList.sunferry.json', 'w', encoding='UTF-8') as f:
  f.write(json.dumps(stopList, ensure_ascii=False))
