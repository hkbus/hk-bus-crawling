# -*- coding: utf-8 -*-

import requests
import json
import time

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
stops = {}

for region in ['HKI', 'KLN', "NT"]:
  r = emitRequest('https://data.etagmb.gov.hk/route/'+region)
  routes = r.json()['data']['routes']
  for route_no in routes:
    r = emitRequest('https://data.etagmb.gov.hk/route/'+region+'/'+route_no)
    for route in r.json()['data']:
      service_type = 2
      for direction in route['directions']:
        rs = emitRequest('https://data.etagmb.gov.hk/route-stop/'+str(route['route_id'])+'/'+str(direction['route_seq']))
        for stop in rs.json()['data']['route_stops']:
          stop_id = stop['stop_id']
          if stop_id not in stops:
            stops[str(stop_id)] = {
              "stop": str(stop_id), 
              "name_en": stop['name_en'], 
              "name_tc": stop['name_tc'], 
            }
        routeList.append({
          "gtfsId": str(route['route_id']),
          "route": route_no,
          "orig_tc": direction['orig_tc'],
          "orig_en": direction['orig_en'],
          "dest_tc": direction['dest_tc'],
          "dest_en": direction['dest_en'],
          "bound": 'O' if direction['route_seq'] == 1 else 'I',
          "service_type": 1 if route["description_tc"] == '正常班次' else service_type,
          "stops": [str(stop['stop_id']) for stop in rs.json()['data']['route_stops']]
        })
        if route["description_tc"] != '正常班次':
          service_type += 1

print ("Route done")

for stop_id in stops.keys():
  r = emitRequest('https://data.etagmb.gov.hk/stop/'+str(stop_id))
  stops[stop_id]['lat'] = r.json()['data']['coordinates']['wgs84']['latitude']
  stops[stop_id]['long'] = r.json()['data']['coordinates']['wgs84']['longitude']

with open('routeList.gmb.json', 'w') as f:
  f.write(json.dumps(routeList, ensure_ascii=False))
with open('stopList.gmb.json', 'w') as f:
  f.write(json.dumps(stops, ensure_ascii=False))
