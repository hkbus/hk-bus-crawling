 # -*- coding: utf-8 -*-
import asyncio
import logging
from crawl_utils import emitRequest
from pyproj import Transformer
import json
import httpx
import csv
import re

res = []
mtrStops = {}
epsgTransformer = Transformer.from_crs('epsg:2326', 'epsg:4326')

def addRes(result, stop, exit, barrierFree):
      lat, lng = epsgTransformer.transform( result['y'], result['x'] )
      res.append({
        "name_en": stop["name_en"],
        "name_zh": stop["name_tc"],
        "name": {
          "en": stop["name_en"],
          "zh": stop["name_tc"],
        },
        "exit": exit,
        "lat": lat, 
        "lng": lng,
        "barrierFree": barrierFree,
      })

async def main():
  a_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, pool=None))
  r = await emitRequest('https://opendata.mtr.com.hk/data/mtr_lines_and_stations.csv', a_client)
  r.encoding = 'utf-8'
  reader = csv.reader(r.text.strip().split("\n") )
  headers = next(reader,None)
  for entry in reader:
    mtrStops[entry[3]] = {
      "name_tc": entry[4],
      "name_en": entry[5],
    }

  r = await emitRequest("https://opendata.mtr.com.hk/data/barrier_free_facilities.csv", a_client)
  r.encoding = 'utf-8'
  reader = csv.reader(r.text.strip().split("\n") )
  for entry in reader:
    if entry[2] == 'Y' and entry[3] != '':
      for exit in re.findall(" [A-Z][\d]*", entry[3]):
        if entry[0] in mtrStops:
          mtrStops[entry[0]][exit.strip()] = True
  
  # crawl exit geolocation
  for key, stop in mtrStops.items():
    if stop['name_tc'] == '':
      continue
    q = '港鐵'+stop['name_tc']+'站進出口'
    r = await emitRequest("https://geodata.gov.hk/gs/api/v1.0.0/locationSearch?q="+q, a_client)
    stopExits = [se for se in r.json() if re.match(r"港鐵\w+站-\w+進出口", se['nameZH'])]
    for se in stopExits:
      i = re.match(r"港鐵\w+站-(\w+)進出口", se['nameZH']).groups()
      addRes(se, stop, i[0], i[0] in stop)
        
  with open('exits.mtr.json', 'w', encoding='UTF-8') as f:
    json.dump(list({(v['name']['zh']+v['exit']): v for v in res}.values()), fp=f, ensure_ascii=False)

if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  logging.getLogger('httpx').setLevel(logging.WARNING)
  asyncio.run(main())