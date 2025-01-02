# -*- coding: utf-8 -*-
import asyncio
import csv
import json
import logging

import httpx

from crawl_utils import emitRequest, get_request_limit

logger = logging.getLogger(__name__)

async def getRouteStop(co):
  a_client = httpx.AsyncClient()
  # parse gtfs service_id
  serviceIdMap = {}
  with open('gtfs/calendar.txt', 'r', encoding="utf-8") as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader, None)
    for [service_id, mon, tue, wed, thur, fri, sat, sun, *tmp] in reader:
      serviceIdMap[service_id] = [mon == "1", tue == "1", wed == "1", thur == "1", fri == "1", sat == "1", sun == "1"]
    serviceIdMap["111"] = [True, True, False, True, True, True, True]

  def mapServiceId(weekdays, serviceIdMap_a):
    for service_id in serviceIdMap_a:
      if all(i == j for i, j in zip(serviceIdMap_a[service_id], weekdays)):
        return service_id
    return 999
    # raise Exception("No service ID for weekdays: "+json.dumps(weekdays))

  def getFreq(headways, serviceIdMap_a):
    freq = {}
    for headway in headways:
      service_id = mapServiceId( headway['weekdays'] , serviceIdMap_a)
      if service_id not in freq:
        freq[service_id] = {}
      freq[service_id][headway['start_time'].replace(':', '')[:4]] = [
        headway['end_time'].replace(':', '')[:4],
        str(headway['frequency'] * 60)
      ] if headway['frequency'] is not None else None
    return freq

  routeList = []
  stops = {}

  stopCandidates = {}

  async def get_route_directions(route, route_no):
    service_type = 2
    for direction in route['directions']:
      rs = await emitRequest('https://data.etagmb.gov.hk/route-stop/'+str(route['route_id'])+'/'+str(direction['route_seq']), a_client)
      for stop in rs.json()['data']['route_stops']:
        stop_id = stop['stop_id']

        # GMB ETA API Spec: "A stop may have different names under different routes"
        # While hk-bus-crawling only allows one name per stop
        # Try to strategically and deterministically pick a stop name
        oldNameEn = stops[str(stop_id)]['name_en'] if str(
            stop_id) in stops else ""
        oldNameTc = stops[str(stop_id)]['name_tc'] if str(
            stop_id) in stops else ""
        newNameEn = stop['name_en'].strip()
        newNameTc = stop['name_tc'].strip()
        useNameEn = oldNameEn
        useNameTc = oldNameTc
        toReplace = False

        # Prefer longer Chinese names. They are usually more specific
        # e.g. "常安街, 柴灣消防局對面" over "常安街77號"
        # e.g. "小西灣道, 香港學術及職業資歷評審局外" over "小西灣道, 近曉翠街"
        # e.g. "暢運道, 近國際都會都會大廈" over "暢運道, 近紅磡站", "紅磡站, 暢運道"
        # Note: "柴灣道, 筲箕灣官立中學外" over "柴灣道, 筲箕灣官立中學"
        # Note: "大坑東道, 大坑東遊樂場外" over "大坑東道,大坑東遊樂場外"
        # Note: "亞皆老街113號, 太平道" over "亞皆老街, 嘉麗園", "亞皆老街, 近嘉麗園", "亞皆老街113號"
        # Note: "貿業路, 寶琳港鐵站外" "Po Lam Station" over "貿業路, 近寶琳站" "Mau Yip Road,
        # near Po Lam Station"
        if len(newNameTc) > len(oldNameTc):
          toReplace = True
        elif len(newNameTc) == len(oldNameTc):
          if newNameTc > oldNameTc:
            toReplace = True
          elif newNameTc == oldNameTc:
            # Prefer English names with more words
            if len(newNameEn.split()) > len(oldNameEn.split()):
              toReplace = True
            elif len(newNameEn.split()) == len(oldNameEn.split()):
              if len(newNameEn) > len(oldNameEn):
                toReplace = True
              elif len(newNameEn) == len(oldNameEn):
                if newNameEn > oldNameEn:
                  toReplace = True
        if toReplace:
          useNameTc = newNameTc
          useNameEn = newNameEn

        if oldNameEn.upper() == newNameEn.upper():
          # Prefer fewer uppercase letters
          # e.g. "Pok Fu Lam Road" over "POK FU LAM ROAD"
          # e.g. "Tsing Yi Heung Sze Wui Road, Near Greenfield Garden Block 3"
          # over "TSING YI HEUNG SZE WUI ROAD, near Greenfield Garden Block 3"
          useNameEn = newNameEn if sum(
              1 for c in newNameEn if c.isupper()) < sum(
              1 for c in oldNameEn if c.isupper()) else oldNameEn

        if str(stop_id) not in stopCandidates:
          stopCandidates[str(stop_id)] = {'en_used': '',
                                          'en_others': set(),
                                          'tc_used': '',
                                          'tc_others': set()}
        stopCandidates[str(stop_id)]['en_used'] = useNameEn
        stopCandidates[str(stop_id)]['en_others'].add(newNameEn)
        stopCandidates[str(stop_id)]['tc_used'] = useNameTc
        stopCandidates[str(stop_id)]['tc_others'].add(newNameTc)

        stops[str(stop_id)] = {
            "stop": str(stop_id),
            "name_en": useNameEn,
            "name_tc": useNameTc,
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
        "freq": getFreq(direction['headways'], serviceIdMap)
      })
      #print(routeList)
      if route["description_tc"] != '正常班次':
        service_type += 1
    
  req_route_limit = asyncio.Semaphore(get_request_limit())
  async def get_route(region:str, route_no):
    async with req_route_limit:
      r = await emitRequest('https://data.etagmb.gov.hk/route/'+region+'/'+route_no, a_client)
      await asyncio.gather(*[get_route_directions(route, route_no) for route in r.json()['data']])
    routeList.sort(key = lambda a: a['gtfsId'])

  req_route_region_limit = asyncio.Semaphore(get_request_limit())
  async def get_routes_region(region: str):
    async with req_route_region_limit:
      r = await emitRequest('https://data.etagmb.gov.hk/route/'+region, a_client)
      await asyncio.gather(*[get_route(region, route) for route in r.json()['data']['routes']])
  
  await asyncio.gather(*[get_routes_region(r) for r in ['HKI', 'KLN', "NT"]])

  with open(f'routeList.{co}.json', 'w', encoding='UTF-8') as f:
    json.dump(routeList, f, ensure_ascii=False)
  logger.info("Route done")


  req_stops_limit = asyncio.Semaphore(get_request_limit())
  with open("gtfs.json", "r", encoding='UTF-8') as f:
    gtfs = json.load(f)
    gtfsStops = gtfs["stopList"]

  async def update_stop_loc(stop_id):
    if stop_id not in gtfsStops:
      logger.info(f"Getting stop {stop_id} from etagmb")
      async with req_stops_limit:
        r = await emitRequest('https://data.etagmb.gov.hk/stop/'+str(stop_id), a_client)
        stops[stop_id]['lat'] = r.json()['data']['coordinates']['wgs84']['latitude']
        stops[stop_id]['long'] = r.json()['data']['coordinates']['wgs84']['longitude']
    else:
      logger.debug(f"Getting stop {stop_id} from gtfs")
      stops[stop_id]['lat'] = gtfsStops[stop_id]['lat']
      stops[stop_id]['long'] = gtfsStops[stop_id]['lng']

  await asyncio.gather(*[update_stop_loc(stop_id) for stop_id in sorted(stops.keys())])

  with open(f'stopList.{co}.json', 'w', encoding='UTF-8') as f:
    json.dump(stops,f, ensure_ascii=False)
  for stop in stopCandidates:
    stopCandidates[stop]["tc_others"].discard(stopCandidates[stop]["tc_used"])
    stopCandidates[stop]["tc_others"] = sorted(
        stopCandidates[stop]["tc_others"])
    stopCandidates[stop]["en_others"].discard(stopCandidates[stop]["en_used"])
    stopCandidates[stop]["en_others"] = sorted(
        stopCandidates[stop]["en_others"])
  with open(f'stopCandidates.{co}.json', 'w', encoding='UTF-8') as f:
    def set_default(obj):
      if isinstance(obj, set):
          return list(obj)
      raise TypeError
    json.dump(stopCandidates, f, ensure_ascii=False, default=set_default)

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    asyncio.run(getRouteStop('gmb'))
