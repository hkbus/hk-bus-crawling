import asyncio
import logging
import zipfile
import httpx
from os import path
import csv
import json
import re
from crawl_utils import emitRequest

def takeFirst(elem):
  return int(elem[0])

async def parseGtfs():
  a_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, pool=None))
  if not path.isfile('gtfs.zip'):
    r = await emitRequest('https://static.data.gov.hk/td/pt-headway-tc/gtfs.zip', a_client)
    open('gtfs.zip', 'wb').write(r.content)

  with zipfile.ZipFile("gtfs.zip", "r") as zip_ref:
    zip_ref.extractall("gtfs")

  routeList = {}
  stopList = {}
  serviceDayMap = {}
  routeJourneyTime = json.load(open('routeTime.json', 'r', encoding='UTF-8'))

  with open('gtfs/routes.txt', 'r', encoding='UTF-8') as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader, None)
    for [route_id, agency_id, route_short_name, route_long_name, route_type, route_url] in reader:
      routeList[route_id] = {
        'co': agency_id.replace('LWB', 'KMB').lower().split('+'),
        'route': route_short_name,
        'stops': {},
        'fares': {},
        'freq': {},
        'orig': {
          'zh': route_long_name.split(' - ')[0],
          'en': '',
        },
        'dest': {
          'zh': route_long_name.split(' - ')[1].replace(' (CIRCULAR)', ''),
          'en': '',
        },
        'jt': routeJourneyTime[route_id]["journeyTime"] if route_id in routeJourneyTime else None
      }
    
  # parse timetable
  with open('gtfs/trips.txt', 'r', encoding='UTF-8') as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader, None)
    for [route_id, service_id, trip_id] in reader:
      [route_id, bound, calendar, start_time] = trip_id.split('-')
      if bound not in routeList[route_id]['freq']:
        routeList[route_id]['freq'][bound] = {}
      if calendar not in routeList[route_id]['freq'][bound]:
        routeList[route_id]['freq'][bound][calendar] = {}
      if start_time not in routeList[route_id]['freq'][bound][calendar]:
        routeList[route_id]['freq'][bound][calendar][start_time] = None

  with open('gtfs/frequencies.txt', 'r', encoding='UTF-8') as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader, None)
    for [trip_id, _start_time, end_time, headway_secs] in reader:
      [route_id, bound, calendar, start_time] = trip_id.split('-')
      routeList[route_id]['freq'][bound][calendar][start_time] = (end_time[0:5].replace(':', ''), headway_secs)

  # parse stop seq
  with open('gtfs/stop_times.txt', 'r', encoding='UTF-8') as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader, None)
    for [trip_id, arrival_time, departure_time, stop_id, stop_sequence, pickup_type, drop_off_type, timepoint] in reader:
      [route_id, bound, service_id, tmp] = trip_id.split('-')
      if bound not in routeList[route_id]['stops']:
        routeList[route_id]['stops'][bound] = {}
      routeList[route_id]['stops'][bound][stop_sequence] = stop_id

  # parse fares
  with open('gtfs/fare_attributes.txt', 'r', encoding='UTF-8') as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader, None)
    for [fare_id,price,currency_type,payment_method,transfers,agency_id] in reader:
      [route_id, bound, on, off] = fare_id.split('-')
      if bound not in routeList[route_id]['fares']:
        routeList[route_id]['fares'][bound] = {}
      if on not in routeList[route_id]['fares'][bound] or routeList[route_id]['fares'][bound][on][1] < int(off):
        routeList[route_id]['fares'][bound][on] = ('0' if price == '0.0000' else price, int(off))

  for route_id  in routeList.keys():
    for bound in routeList[route_id]['stops'].keys():
      _tmp = list(routeList[route_id]['stops'][bound].items())
      _tmp.sort(key=takeFirst)
      routeList[route_id]['stops'][bound] = [v for k,v in _tmp]
    for bound in routeList[route_id]['fares'].keys():
      _tmp = list(routeList[route_id]['fares'][bound].items())
      _tmp.sort(key=takeFirst)
      routeList[route_id]['fares'][bound] = [v[0] for k,v in _tmp]

  nameReg = re.compile('\[(.*)\] (.*)')
  def parseStopName(name):
    ret = {}
    for str in name.split('|'):
      matches = nameReg.findall(str)
      if len(matches) == 0: return { "unknown": str }
      for co, gtfsName in matches:
        x, y = co.split('+'), gtfsName.split('/<BR>')
        for i in range(len(x)):
          ret[x[i].lower().replace('lwb', 'kmb')] = y[i if i < len(y) else 0]
    return ret
    

  with open('gtfs/stops.txt', 'r', encoding='UTF-8') as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader, None)
    for [stop_id,stop_name,stop_lat,stop_lon,zone_id,location_type,stop_timezone] in reader:
      stopList[stop_id] = {
        'stopId': stop_id,
        'stopName': parseStopName(stop_name),
        'lat': float(stop_lat),
        'lng': float(stop_lon) 
      }

  with open('gtfs/calendar.txt', 'r', encoding='UTF-8') as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader, None)
    for line in reader:
      [service_id,mon,tue,wed,thur,fri,sat,sun, start_date, end_date] = line
      serviceDayMap[service_id] = [sun, mon, tue, wed, thur, fri, sat]

  with open('gtfs.json', 'w', encoding='UTF-8') as f:
    f.write(json.dumps({
      'routeList': routeList,
      'stopList': stopList,
      "serviceDayMap": serviceDayMap,
    }, ensure_ascii=False, indent=2))

if __name__=='__main__':
  logging.basicConfig(level=logging.INFO)
  logging.getLogger('httpx').setLevel(logging.WARNING)
  logger = logging.getLogger(__name__)
  asyncio.run(parseGtfs())
