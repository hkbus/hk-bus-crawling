# MTR Bus fetching

import csv
import requests
import json

routeList = {}
stopList = {}

r = requests.get('https://opendata.mtr.com.hk/data/mtr_bus_routes.csv')
reader = csv.reader(r.text.split("\n") )
headers = next(reader,None)
routes = [route for route in reader if len(route) == 3]
for [route, chn, eng] in routes:
  if route == '':
    continue;
  start = {
    "zh": chn.split('至')[0],
    "en": eng.split(' to ')[0]
  }
  end = {
    "zh": chn.split('至')[1],
    "en": eng.split(' to ')[1]
  }
  for bound in ['I', 'O']:
    routeList[route+"_"+bound] = {
      "route": route,
      "bound": bound,
      "service_type": "1",
      "orig_tc": start['zh'] if bound == 'O' else end['zh'],
      "dest_tc": end["zh"] if bound == 'O' else start['zh'],
      "orig_en": start['en'] if bound == 'O' else end['en'],
      "dest_en": end["en"] if bound == 'O' else start['en'],
      "stops": []
    }

# handy work from https://opendata.mtr.com.hk/doc/MTR_BUS_DataDictionary_v1.0.pdf
# MTR_bus.csv is prepared by labour work
with open('MTR_bus.csv') as csvfile:
  reader = csv.reader(csvfile)
  headers = next(reader, None)
  for [route, bound, stationId, lat, lng, name_zh, name_en] in reader:
    routeKey = route+"_"+bound
    if routeKey in routeList:
      routeList[routeKey]['stops'].append(stationId)
    else:
      print ("error")
    stopList[stationId] = {
      "stop": stationId,
      "name_en": name_en,
      "name_tc": name_zh,
      "lat": lat,
      "long": lng
    }

with open('routeList.lrtfeeder.json', 'w') as f:
  f.write(json.dumps([route for route in routeList.values() if len(route['stops']) > 0], ensure_ascii=False))
with open('stopList.lrtfeeder.json', 'w') as f:
  f.write(json.dumps(stopList, ensure_ascii=False))