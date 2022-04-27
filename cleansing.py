import json

def isNameMatch(name_a, name_b):
  tmp_a = name_a.lower()
  tmp_b = name_b.lower()
  return tmp_a.find(tmp_b) >= 0 or tmp_b.find(tmp_a) >= 0

def countBus(freq):
  if freq is None: return 0
  sum = 0
  for entries in freq.values():
    for startTime, v in entries.items():
      if v is None: 
        sum += 1
        continue
      endTime, waitTime = v
      sum += int ( ( int(endTime[0:2]) - int(startTime[0:2]) ) * 60 + int(endTime[2:4]) - int(startTime[2:4]) ) / ( int(waitTime) / 60 ) 
  return sum

def cleansing(co):
  with open('routeFareList.%s.json' % co) as f:
    routeList = json.load(f)
  
  for i in range(len(routeList)):
    route = routeList[i]
    if 'skip' in route or 'freq' in route:
      continue
    bestIdx, maxBus = -1, 0
    for j in range(len(routeList)):
      if i == j: continue
      _route = routeList[j]
      if route['route'] == _route['route'] and sorted(route['co']) == sorted(_route['co']) and \
        isNameMatch(route['orig_en'], _route['orig_en']) and isNameMatch(route['dest_en'], _route['dest_en']):
        if 'freq' not in _route: continue
        bus = countBus(_route['freq'])
        if bus > maxBus:
          bestIdx = j
          maxBus = bus
    if bestIdx != -1:
      routeList[bestIdx]['service_type'] = 1 if 'service_type' not in routeList[i] else routeList[bestIdx]['service_type']
      routeList[i]['skip'] = True

  _routeList = [route for route in routeList if 'skip' not in route]
  print (co, len(routeList), len(_routeList))
  
  with open('routeFareList.%s.cleansed.json' % co, 'w') as f:
    f.write(json.dumps(_routeList, ensure_ascii=False))
  

cleansing ('kmb')
cleansing ('nwfb')
cleansing ('ctb')
cleansing ('nlb')
cleansing ('lrtfeeder')
cleansing ('gmb')
cleansing ('lightRail')
cleansing ('mtr')