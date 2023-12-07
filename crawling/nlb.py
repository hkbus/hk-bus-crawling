import asyncio
import json
import logging
from os import path

import httpx

logger=logging.getLogger(__name__)

async def emitRequest(url:str, client:httpx.AsyncClient):
  # retry if "Too many request (429)"
  while True:
    r = await client.get(url)
    if r.status_code == 200:
      return r
    elif r.status_code == 429 or r.status_code == 502:
      await asyncio.sleep(1)
    else:
      r.raise_for_status()
      raise Exception(r.status_code, url)

async def getRouteStop(co):
    # define output name
    ROUTE_LIST = 'routeList.'+co+'.json'
    STOP_LIST = 'stopList.'+co+'.json'

    a_client = httpx.AsyncClient()
    # load route list and stop list if exist
    routeList = []
    if path.isfile(ROUTE_LIST):
        logger.warning(f"{ROUTE_LIST} already exist, skipping...")
        return
    else:
        # load routes
        r = await emitRequest('https://rt.data.gov.hk/v2/transport/nlb/route.php?action=list', a_client)
        for route in r.json()['routes']:
            routeList.append({
                "id": route['routeId'],
                "route": route['routeNo'],
                "bound": "O",
                "orig_en": route['routeName_e'].split(' > ')[0],
                "orig_tc": route['routeName_c'].split(' > ')[0],
                "dest_en": route['routeName_e'].split(' > ')[1],
                "dest_tc": route['routeName_c'].split(' > ')[1],
                "service_type": str(1 + route['overnightRoute'] * 2 + route['specialRoute'] *4),
                "stops": [],
                "co": ["nlb"]
            })
        logger.info("Digested route list")

    stopList = {}
    if path.isfile(STOP_LIST):
        with open(STOP_LIST) as f:
            stopList = json.load(f)
   
    async def getRouteStop(routeId):
        r = await emitRequest('https://rt.data.gov.hk/v2/transport/nlb/stop.php?action=list&routeId='+routeId, a_client)
        try:
            return r.json()['stops']
        except Exception as err:
            print(r)
            raise err

    async def addRouteStop(route):
        stops = await getRouteStop(route['id'])
        stopIds = []
        fares = []
        faresHoliday = []
        for stop in stops:
            if stop['stopId'] not in stopList:
                stopList[stop['stopId']] = {
                    'stop': stop['stopId'],
                    'name_en': stop['stopName_e'],
                    'name_tc': stop['stopName_c'],
                    'lat': stop['latitude'],
                    'long': stop['longitude']
                }
            stopIds.append(stop['stopId'])
            fares.append(stop['fare'])
            faresHoliday.append(stop['fareHoliday'])
        route['stops'] = stopIds
        route['fares'] = fares[0:-1]
        route['faresHoliday'] = faresHoliday[0:-1]

    async def getRouteStopList ():
        await asyncio.gather(*[addRouteStop(r) for r in routeList])
        logger.info("Digested stop list")
        return routeList

    await getRouteStopList()

    with open(ROUTE_LIST, 'w') as rf, open(STOP_LIST, 'w') as sf:
        json.dump(routeList, rf, ensure_ascii=False)
        json.dump(stopList, sf, ensure_ascii=False)
    logger.info("Dumped lists")

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    asyncio.run(getRouteStop('nlb'))