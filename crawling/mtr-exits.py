 # -*- coding: utf-8 -*-
import asyncio
import logging
from crawl_utils import emitRequest
from pyproj import Transformer
import json
import string
import httpx

res = []
epsgTransformer = Transformer.from_crs('epsg:2326', 'epsg:4326')

def checkResult(results, q, stop, exit):
  for result in results:
    if result['nameZH'] == q:
      lat, lng = epsgTransformer.transform( result['y'], result['x'] )
      res.append({
        "station": stop["stop"],
        "name_en": stop["name_en"],
        "name_zh": stop["name_tc"],
        "exit": exit,
        "lat": lat, 
        "lng": lng
      })
      print(q)
      return True
  return False

async def main():
  a_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, pool=None))
  stops = json.load(open('stopList.mtr.json', 'r'))
  for key, stop in stops.items():
    print(stop['name_tc'])
    q = '港鐵'+stop['name_tc']+'站進出口'
    r = await emitRequest("https://geodata.gov.hk/gs/api/v1.0.0/locationSearch?q="+q, a_client)
    for char in string.ascii_uppercase:
      q = '港鐵'+stop['name_tc']+'站-'+str(char)+'進出口'
      checkResult(r.json(), q, stop, char)
      for i in range(1,10):
        q = '港鐵'+stop['name_tc']+'站-'+char+str(i)+'進出口'
        checkResult(r.json(), q, stop, char+str(i))
        
  with open('exits.mtr.json', 'w', encoding='UTF-8') as f:
    f.write(json.dumps(res, ensure_ascii=False))

if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  logging.getLogger('httpx').setLevel(logging.WARNING)
  asyncio.run(main())