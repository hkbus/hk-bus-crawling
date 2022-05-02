import json
import requests

with open( 'routeFareList.json' ) as f:
  newDb = json.load(f)

r = requests.get('https://hkbus.github.io/hk-bus-crawling/routeFareList.json')
oldDb = r.json()

for newKey in newDb['routeList']:
  if newKey not in oldDb['routeList']:
    print ('new '+newKey)

for oldKey in oldDb['routeList']:
  if oldKey not in newDb['routeList']:
    print ('old '+oldKey)