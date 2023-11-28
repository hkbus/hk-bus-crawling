import requests
import json
import re
import os
import zipfile
import io

r = requests.get("https://static.csdi.gov.hk/csdi-webpage/download/common/51bbe0d88d421c1e94572e503ad0428fabe11e3300c40e221146550044e54de5")
z = zipfile.ZipFile(io.BytesIO(r.content))
with z.open("FB_ROUTE_LINE.json") as f:
  data = json.loads(re.sub(r"([0-9]+\.[0-9]{6})[0-9]+", r"\1", f.read().decode("utf-8")).replace("\n", ""))

print (data["type"])
os.makedirs("waypoints", exist_ok=True)

for feature in data["features"]:
  properties = feature["properties"]
  with open("waypoints/"+str(properties["ROUTE_ID"])+"-"+("O" if properties["ROUTE_SEQ"] == 1 else "I")+".json", "wt") as f:
    f.write(json.dumps({
      "features": [feature],
      "type": "FeatureCollection"
    }, ensure_ascii=False))
