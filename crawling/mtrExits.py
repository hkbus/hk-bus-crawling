# -*- coding: utf-8 -*-
import asyncio
import logging
from crawl_utils import emitRequest
from pyproj import Transformer
import json
import string
import httpx
import csv
import re

res = []
mtrStops = {}
epsgTransformer = Transformer.from_crs('epsg:2326', 'epsg:4326')


def checkResult(results, q, stop, exit, barrierFree):
  for result in results:
    if result['nameZH'] == q:
      lat, lng = epsgTransformer.transform(result['y'], result['x'])
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
      return True
  return False


async def main():
  a_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, pool=None))
  r = await emitRequest('https://opendata.mtr.com.hk/data/mtr_lines_and_stations.csv', a_client)
  r.encoding = 'utf-8'
  reader = csv.reader(r.text.strip().split("\n"))
  headers = next(reader, None)
  for entry in reader:
    mtrStops[entry[3]] = {
        "name_tc": entry[4],
        "name_en": entry[5],
    }

  r = await emitRequest("https://opendata.mtr.com.hk/data/barrier_free_facilities.csv", a_client)
  r.encoding = 'utf-8'
  reader = csv.reader(r.text.strip().split("\n"))
  for entry in reader:
    if entry[2] == 'Y' and entry[3] != '':
      for exit in re.findall(" [A-Z][\\d]*", entry[3]):
        if entry[0] in mtrStops:
          mtrStops[entry[0]][exit.strip()] = True

  # crawl exit geolocation
  for key, stop in mtrStops.items():
    q = '港鐵' + stop['name_tc'] + '站進出口'
    r = await emitRequest("https://geodata.gov.hk/gs/api/v1.0.0/locationSearch?q=" + q, a_client)
    for char in string.ascii_uppercase:
      q = '港鐵' + stop['name_tc'] + '站-' + str(char) + '進出口'
      checkResult(r.json(), q, stop, char, str(char) in stop)
      for i in range(1, 10):
        q = '港鐵' + stop['name_tc'] + '站-' + char + str(i) + '進出口'
        checkResult(
            r.json(),
            q,
            stop,
            char + str(i),
            (char + str(char)) in stop)

  with open('exits.mtr.json', 'w', encoding='UTF-8') as f:
    f.write(json.dumps(list(
        {(v['name']['zh'] + v['exit']): v for v in res}.values()), ensure_ascii=False))

if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  logging.getLogger('httpx').setLevel(logging.WARNING)
  asyncio.run(main())
