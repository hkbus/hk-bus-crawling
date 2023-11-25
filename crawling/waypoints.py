import requests
import json
import re
import os
import asyncio

r = requests.get('https://api.csdi.gov.hk/apim/dataquery/api/?id=td_rcd_1638844988873_41214&layer=fb_route_line&limit=1')
r.encoding = 'utf-8'
data = json.loads(r.text)
cnt = data["numberMatched"]

os.makedirs("waypoints", exist_ok=True)

def getWaypoints(offset):
  r = requests.get('https://api.csdi.gov.hk/apim/dataquery/api/?id=td_rcd_1638844988873_41214&layer=fb_route_line&limit=50&offset='+str(offset))
  r.encoding = 'utf-8'
  data = json.loads(re.sub(r"([0-9]+\.[0-9]{6})[0-9]+", r"\1", r.text).replace("\n", ""))
  for feature in data["features"]:
    properties = feature["properties"]
    with open("waypoints/"+str(properties["ROUTE_ID"])+"-"+str(properties["ROUTE_SEQ"])+".json", "w") as f:
      f.write(json.dumps({
        "timeStamp": data["timeStamp"],
        "features": [feature],
        "type": "FeatureCollection"
      }, ensure_ascii=False))
  
loop = asyncio.get_event_loop()
futures = [loop.run_in_executor(None, getWaypoints, offset) for offset in range(0, cnt+1, 50)]
