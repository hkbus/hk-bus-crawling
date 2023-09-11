import zipfile
import requests
from os import path
import csv
import json
import codecs

if not path.isfile('holiday.json'):
  r = requests.get('https://www.1823.gov.hk/common/ical/tc.json')
  data = json.loads(r.content.decode('utf-8-sig'))
  with open('holiday.json', 'w') as f:
    f.write(json.dumps([holiday['dtstart'][0] for holiday in data['vcalendar'][0]['vevent']]))
    
