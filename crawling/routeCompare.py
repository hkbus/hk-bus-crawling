# -*- coding: utf-8 -*-
# Check route lateset update time

import requests
import json
import os
import time
import xxhash
import re

r = requests.get("https://data.hkbus.app/routeFareList.min.json")
r.encoding = 'utf-8'
oldDb = r.json()
newDb = json.load(open('routeFareList.min.json', 'r', encoding='utf-8'))

os.makedirs("route-ts", exist_ok=True)

def isRouteEqual(a, b):
  return xxhash.xxh3_64(str(a)).hexdigest() == xxhash.xxh3_64(str(b)).hexdigest()

for newKey in newDb['routeList']:
  if newKey not in oldDb['routeList'] or not isRouteEqual(oldDb['routeList'][newKey], newDb['routeList'][newKey]):
    filename = re.sub(r'[\\\/\:\*\?\"\<\>\|]', '', newKey).upper()
    with open(os.path.join("route-ts", filename), "w", encoding='utf-8') as f:
      f.write(str(int(time.time())))

for oldKey in oldDb['routeList']:
  if oldKey not in newDb['routeList']:
    filename = re.sub(r'[\\\/\:\*\?\"\<\>\|]', '', oldKey).upper()
    with open(os.path.join("route-ts", filename), "w", encoding='utf-8') as f:
      f.write(str(int(time.time())))