# -*- coding: utf-8 -*-
# Check route lateset update time

import requests
import json
import os
import time

r = requests.get("https://data.hkbus.app/routeFareList.min.json")
r.encoding = 'utf-8'
oldDb = r.json()
newDb = json.load(open('routeFareList.min.json', 'r', encoding='UTF-8'))

os.makedirs("route-ts", exist_ok=True)

def isRouteEqual(a, b):
  if a["bound"] != b["bound"] or b["freq"] != a["freq"] or a["orig"] != b["orig"] or a["dest"] != b["dest"] or a["faresHoliday"] != b["faresHoliday"] or a["fares"] != b["fares"] or a["stops"] != b["stops"]:
    return False
  return True

for newKey in newDb['routeList']:
  updated = False
  if newKey not in oldDb['routeList'] or not isRouteEqual(oldDb['routeList'][newKey], newDb['routeList'][newKey]):
    with open("route-ts/"+newKey, "w") as f:
      f.write(str(int(time.time())))
    
for oldKey in oldDb['routeList']:
  if oldKey not in newDb['routeList']:
    with open("route-ts/"+oldKey, "w") as f:
      f.write(str(int(time.time())))