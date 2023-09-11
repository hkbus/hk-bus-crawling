import xml.etree.ElementTree as ET
import requests
from os import path

if not path.isfile('ROUTE_BUS.xml'):
  r = requests.get('https://static.data.gov.hk/td/routes-fares-xml/ROUTE_BUS.xml')
  r.encoding = 'utf-8'
  with open('ROUTE_BUS.xml', 'w') as f:
    f.write(r.text)

routeTimeList = {}
tree = ET.parse('ROUTE_BUS.xml')
root = tree.getroot()
for route in root.iter('ROUTE'):
  if route.find('ROUTE_TYPE').text == '1':
    routeTimeList[route.find('ROUTE_ID').text] = {
      'co': route.find('COMPANY_CODE').text.replace('LWB', 'KMB').lower().split('+'),
      'route': route.find('ROUTE_NAMEC').text,
      'journeyTime': route.find('JOURNEY_TIME').text,
    }

import json
with open('routeTime.json', 'w') as f:
  f.write(json.dumps(routeTimeList, ensure_ascii=False))