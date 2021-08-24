import zipfile
import requests
from os import path
import csv
import json

if not path.isfile('gtfs.zip'):
  r = requests.get('https://static.data.gov.hk/td/pt-headway-tc/gtfs.zip')
  open('gtfs.zip', 'wb').write(r.content)

with zipfile.ZipFile("gtfs.zip","r") as zip_ref:
  zip_ref.extractall("gtfs")

with open('routeFare.json') as f:
  routeFare = json.load(f)

def takeFirst(elem):
  return elem[0]

with open('gtfs/trips.txt') as csvfile:
  reader = csv.reader(csvfile)
  headers = next(reader, None)
  for [route_id, service_id, trip_id] in reader:
    [route_id, bound, calendar, start_time] = trip_id.split('-')
    if route_id not in routeFare:
      continue
    if 'freq' not in routeFare[route_id]:
      routeFare[route_id]['freq'] = {}
    if bound not in routeFare[route_id]['freq']:
      routeFare[route_id]['freq'][bound] = {}
    if calendar not in routeFare[route_id]['freq'][bound]:
      routeFare[route_id]['freq'][bound][calendar] = {}
    if start_time not in routeFare[route_id]['freq'][bound][calendar]:
      routeFare[route_id]['freq'][bound][calendar][start_time] = None

with open('gtfs/frequencies.txt') as csvfile:
  reader = csv.reader(csvfile)
  headers = next(reader, None)
  for [trip_id, _start_time, end_time, headway_secs] in reader:
    [route_id, bound, calendar, start_time] = trip_id.split('-')
    if route_id not in routeFare:
      continue
    routeFare[route_id]['freq'][bound][calendar][start_time] = (end_time[0:5].replace(':', ''), headway_secs)

with open('routeTimetable.json', 'w') as f:
    f.write(json.dumps(routeFare, ensure_ascii=False))
