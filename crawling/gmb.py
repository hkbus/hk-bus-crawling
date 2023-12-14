# -*- coding: utf-8 -*-
import asyncio
import csv
import json
import logging

import httpx

from crawling.crawl_utils import emitRequest

logger = logging.getLogger(__name__)

REQUEST_LIMIT = 10

async def getRouteStop(co):
  a_client = httpx.AsyncClient()
  # parse gtfs service_id
  serviceIdMap = {}
  with open('gtfs/calendar.txt') as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader, None)
    for [service_id, mon, tue, wed, thur, fri, sat, sun, *tmp] in reader:
      serviceIdMap[service_id] = [mon == "1", tue == "1", wed == "1", thur == "1", fri == "1", sat == "1", sun == "1"]
    serviceIdMap["111"] = [True, True, False, True, True, True, True]

  def mapServiceId(weekdays):
    for service_id in serviceIdMap:
      if all(i == j for i, j in zip(serviceIdMap[service_id], weekdays)):
        return service_id
    return 999
    raise Exception("No service ID for weekdays: "+json.dumps(weekdays))

  def getFreq(headways):
    freq = {}
    for headway in headways:
      service_id = mapServiceId( headway['weekdays'] )
      if service_id not in freq:
        freq[service_id] = {}
      freq[service_id][headway['start_time'].replace(':', '')[:4]] = [
        headway['end_time'].replace(':', '')[:4],
        str(headway['frequency'] * 60)
      ] if headway['frequency'] is not None else None
    return freq

  routeList = []
  stops = {}

  async def get_route_directions(route, route_no):
    service_type = 2
    for direction in route['directions']:
      rs = await emitRequest('https://data.etagmb.gov.hk/route-stop/'+str(route['route_id'])+'/'+str(direction['route_seq']), a_client)
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
        "stops": [str(stop['stop_id']) for stop in rs.json()['data']['route_stops']],
        "freq": getFreq(direction['headways'])
      })
      #print(routeList)
      if route["description_tc"] != '正常班次':
        service_type += 1
    
  req_route_limit = asyncio.Semaphore(REQUEST_LIMIT)
  async def get_route(region:str, route_no):
    async with req_route_limit:
      r = await emitRequest('https://data.etagmb.gov.hk/route/'+region+'/'+route_no, a_client)
      await asyncio.gather(*[get_route_directions(route, route_no) for route in r.json()['data']])

  req_route_region_limit = asyncio.Semaphore(REQUEST_LIMIT)
  async def get_routes_region(region: str):
    async with req_route_region_limit:
      r = await emitRequest('https://data.etagmb.gov.hk/route/'+region, a_client)
      await asyncio.gather(*[get_route(region, route) for route in r.json()['data']['routes']])
  
  await asyncio.gather(*[get_routes_region(r) for r in ['HKI', 'KLN', "NT"]])

  with open(f'routeList.{co}.json', 'w') as f:
    json.dump(routeList, f, ensure_ascii=False)
  logger.info("Route done")

  req_stops_limit = asyncio.Semaphore(REQUEST_LIMIT)
  async def update_stop_loc(stop_id):
    async with req_stops_limit:
      r = await emitRequest('https://data.etagmb.gov.hk/stop/'+str(stop_id), a_client)
      stops[stop_id]['lat'] = r.json()['data']['coordinates']['wgs84']['latitude']
      stops[stop_id]['long'] = r.json()['data']['coordinates']['wgs84']['longitude']

  await asyncio.gather(*[update_stop_loc(stop_id) for stop_id in sorted(stops.keys())])

  with open(f'stopList.{co}.json', 'w') as f:
    json.dump(stops,f, ensure_ascii=False)

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    # logging.getLogger('httpx').setLevel(logging.WARNING)
    asyncio.run(getRouteStop('gmb'))
