import asyncio
import json
import logging
from os import path

import httpx

from crawl_utils import emitRequest, get_request_limit

logger = logging.getLogger(__name__)


async def getRouteStop(co):
  a_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, pool=None))
  # define output name
  ROUTE_LIST = 'routeList.' + co + '.json'
  STOP_LIST = 'stopList.' + co + '.json'

  # load route list and stop list if exist
  routeList = {}
  if path.isfile(ROUTE_LIST):
    return
  else:
    # load routes
    r = await emitRequest('https://rt.data.gov.hk/v2/transport/citybus/route/' + co, a_client)
    routeList = r.json()['data']

  _stops = []
  stopList = {}
  if path.isfile(STOP_LIST):
    with open(STOP_LIST, 'r', encoding='UTF-8') as f:
      stopList = json.load(f)

  # function to load single stop info
  req_stop_list_limit = asyncio.Semaphore(get_request_limit())

  async def getStop(stopId):
    async with req_stop_list_limit:
      r = await emitRequest('https://rt.data.gov.hk/v2/transport/citybus/stop/' + stopId, a_client)
    return r.json()['data']

  # function to async load multiple stops info
  async def getStopList(stops):
    ret = await asyncio.gather(*[getStop(stop) for stop in stops])
    return ret

  req_route_stop_limit = asyncio.Semaphore(get_request_limit())

  async def getRouteStop(param):
    co, route = param
    if route.get('bound', 0) != 0 or route.get('stops', {}):
      return route
    route['stops'] = {}
    for direction in ['inbound', 'outbound']:
      r = await emitRequest('https://rt.data.gov.hk/v2/transport/citybus/route-stop/' + co.upper() + '/' + route['route'] + "/" + direction, a_client)
      route['stops'][direction] = [stop['stop'] for stop in r.json()['data']]
    return route

  async def getRouteStopList():
    ret = await asyncio.gather(*[getRouteStop((co, route))
                                 for route in routeList])
    return ret

  routeList = await getRouteStopList()
  for route in routeList:
    for direction, stops in route['stops'].items():
      for stopId in stops:
        _stops.append(stopId)

  # load stops for this route aync
  _stops = sorted(set(_stops))

  stopInfos = list(zip(_stops, await getStopList(_stops)))
  for stopId, stopInfo in stopInfos:
    stopList[stopId] = stopInfo

  _routeList = []
  for route in routeList:
    if route.get('bound', 0) != 0:
      _routeList.append(route)
      continue
    for bound in ['inbound', 'outbound']:
      if len(route['stops'][bound]) > 0:
        _routeList.append({
            'co': co,
            'route': route['route'],
            'bound': 'O' if bound == 'outbound' else 'I',
            'orig_en': route['orig_en'] if bound == 'outbound' else route['dest_en'],
            'orig_tc': route['orig_tc'] if bound == 'outbound' else route['dest_tc'],
            'dest_en': route['dest_en'] if bound == 'outbound' else route['orig_en'],
            'dest_tc': route['dest_tc'] if bound == 'outbound' else route['orig_tc'],
            'stops': list(filter(lambda stopId: bool(stopList[stopId]), route['stops'][bound])),
            'serviceType': 0
        })

  with open(ROUTE_LIST, 'w', encoding='UTF-8') as f:
    f.write(json.dumps(_routeList, ensure_ascii=False))
  with open(STOP_LIST, 'w', encoding='UTF-8') as f:
    f.write(json.dumps(stopList, ensure_ascii=False))

if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  logging.getLogger('httpx').setLevel(logging.WARNING)
  asyncio.run(getRouteStop('ctb'))
