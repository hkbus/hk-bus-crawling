import requests
import json
from os import path
import asyncio

def getRouteStop(co):
    # define output name
    ROUTE_LIST = 'routeList.'+co+'.json'
    STOP_LIST = 'stopList.'+co+'.json'

    # load route list and stop list if exist
    routeList = {}
    if path.isfile(ROUTE_LIST):
        return
    else:
        # load routes
        r = requests.get('https://rt.data.gov.hk/v1/transport/nlb/route.php?action=list')
        routeList = []
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

    _stops = []
    stopList = {}
    if path.isfile(STOP_LIST):
        with open(STOP_LIST) as f:
            stopList = json.load(f)
   
    def getRouteStop(routeId):
        r = requests.post('https://rt.data.gov.hk/v1/transport/nlb/stop.php?action=list', data = '{"routeId": "'+routeId+'"}')
        return r.json()['stops']

    async def getRouteStopList ():
        loop = asyncio.get_event_loop()
        futures = [loop.run_in_executor(None, getRouteStop, route['id']) for route in routeList]
        ret = []
        for future in futures:
            ret.append(await future)
        for route, stops in zip(routeList, ret):
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
        return routeList


    loop = asyncio.get_event_loop()
    routeList = loop.run_until_complete(getRouteStopList())

    with open(ROUTE_LIST, 'w') as f:
        f.write(json.dumps(routeList, ensure_ascii=False))
    with open(STOP_LIST, 'w') as f:
        f.write(json.dumps(stopList, ensure_ascii=False))

getRouteStop('nlb')
