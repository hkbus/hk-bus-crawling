import json
from sys import stderr
from haversine import haversine, Unit

routeList = []
stopList = {}
stopMap = {}

def getRouteObj ( route, co, stops, bound, orig, dest, seq, fares, faresHoliday, freq, jt, nlbId, gtfsId, serviceType = 1):
  return {
    'route': route,
    'co': co,
    'stops': stops,
    'serviceType': serviceType,
    'bound': bound,
    'orig': orig,
    'dest': dest,
    'fares': fares,
    'faresHoliday': faresHoliday,
    'freq': freq,
    'jt': jt,
    'nlbId': nlbId,
    'gtfsId': gtfsId,
    'seq': seq
  }

def isGtfsMatch(knownRoute, newRoute):
  if knownRoute['gtfsId'] is None: return True
  if 'gtfs' not in newRoute: return True 

  return knownRoute['gtfsId'] in newRoute['gtfs']
  
def importRouteListJson( co ):
  _routeList = json.load(open('routeFareList.%s.cleansed.json'%co))
  _stopList = json.load(open('stopList.%s.json'%co))
  for stopId, stop in _stopList.items():
    if stopId not in stopList:
      try:
        stopList[stopId] = {
          'name': {
            'en': stop['name_en'],
            'zh': stop['name_tc']
          },
          'location': {
            'lat': float(stop['lat']),
            'lng': float(stop['long'])
          }
        }
      except:
        print("Problematic stop: ", stopId, file=stderr)
  
  for _route in _routeList:
    found = False
    orig = {'en': _route['orig_en'].replace('/', '／'), 'zh': _route['orig_tc'].replace('/', '／')}
    dest = {'en': _route['dest_en'].replace('/', '／'), 'zh': _route['dest_tc'].replace('/', '／')}
    
    for route in routeList:
      if _route['route'] == route['route'] and co in route['co'] and isGtfsMatch(route, _route):
        # skip checking if the bound is not the same
        if co in route["bound"] and route['bound'][co] != _route['bound']:
          continue
        
        if len(_route['stops']) == route['seq']:
          dist = 0
          merge = True
          for stop_a, stop_b in zip( _route['stops'], route['stops'][0][1] ):
            stop_a = stopList[stop_a]
            stop_b = stopList[stop_b]
            dist = haversine( 
              (stop_a['location']['lat'], stop_a['location']['lng']), 
              (stop_b['location']['lat'], stop_b['location']['lng']) 
            ) * 1000 # in meter 
            merge = merge and dist < 300
          if merge:
            found = True
            route['stops'].append((co, _route['stops']))
            route['bound'][co] = _route['bound']
            for i in range(0, route['seq']):
              if route['stops'][0][0] == co:
                # skip if same company
                continue
              if route['stops'][0][1][i] not in stopMap:
                stopMap[route['stops'][0][1][i]] = [(co, _route['stops'][i])]
              elif (co, _route['stops'][i]) not in stopMap[route['stops'][0][1][i]]:
                stopMap[route['stops'][0][1][i]].append( (co, _route['stops'][i]) )
              if _route['stops'][i] not in stopMap:
                stopMap[_route['stops'][i]] = [(route['stops'][0][0], route['stops'][0][1][i])]
              elif (route['stops'][0][0], route['stops'][0][1][i]) not in stopMap[_route['stops'][i]]:
                stopMap[_route['stops'][i]].append( (route['stops'][0][0], route['stops'][0][1][i]) )

    if not found:
      routeList.append( 
        getRouteObj(
          route = _route['route'], 
          co = _route['co'], 
          serviceType = _route.get('service_type', 1), 
          stops = [(co, _route['stops'])],
          bound = {co: _route['bound']},
          orig = orig,
          dest = dest,
          fares = _route.get('fares', None),
          faresHoliday = _route.get('faresHoliday', None),
          freq = _route.get('freq', None),
          jt = _route.get('jt', None),
          nlbId = _route.get('id', None),
          gtfsId = _route.get('gtfsId', _route.get('gtfs', [None])[0]),
          seq = len(_route['stops'])
        )
      )

def isMatchStops(stops_a, stops_b, debug = False):
  if len(stops_a) != len(stops_b):
    return False
  for v in stops_a:
    if stopMap.get(v, [[None,None]])[0][1] in stops_b:
      return True
  return False

def getRouteId(v):
  return '%s+%s+%s+%s'%(v['route'], v['serviceType'], v['orig']['en'], v['dest']['en'])

def smartUnique():
  _routeList = []
  for i in range(len(routeList)):
    if routeList[i].get('skip', False):
      continue
    founds = []
    # compare route one-by-one
    for j in range(i+1, len(routeList)):
      if routeList[i]['route'] == routeList[j]['route'] \
        and len(routeList[i]['stops']) == len(routeList[j]['stops']) \
        and len([co for co in routeList[i]['co'] if co in routeList[j]['co']]) == 0 \
        and isMatchStops(routeList[i]['stops'][0][1], routeList[j]['stops'][0][1]):
        founds.append( j )
      elif routeList[i]['route'] == routeList[j]['route'] \
        and str(routeList[i]['serviceType']) == str(routeList[j]['serviceType']) \
        and routeList[i]['orig']['en'] == routeList[j]['orig']['en'] \
        and routeList[i]['dest']['en'] == routeList[j]['dest']['en']:
        routeList[j]['serviceType'] = str(int(routeList[j]['serviceType'])+1)

    # update obj
    for found in founds:
      routeList[i]['co'].extend(routeList[found]['co'])
      routeList[i]['stops'].extend( routeList[found]['stops'] )
      routeList[found]['skip'] = True

    # append return array
    _routeList.append(routeList[i])

  return _routeList
      
importRouteListJson('kmb')
importRouteListJson('nwfb')
importRouteListJson('ctb')
importRouteListJson('nlb')
importRouteListJson('lrtfeeder')
importRouteListJson('gmb')
importRouteListJson('lightRail')
importRouteListJson('mtr')
routeList = smartUnique()
for route in routeList:
  route['stops'] = {co: stops for co, stops in route['stops']}

holidays = json.load(open('holiday.json'))

def standardizeDict(d):
  return {key: value if not isinstance(value, dict) else standardizeDict(value) for key, value in sorted(d.items())}

db = standardizeDict({
  'routeList': {getRouteId(v): v for v in routeList},
  'stopList': stopList,
  'stopMap': stopMap,
  'holidays': holidays
})

with open( 'routeFareList.json', 'w' ) as f:
  f.write(json.dumps(db, ensure_ascii=False, indent=4))

with open( 'routeFareList.min.json', 'w' ) as f:
  f.write(json.dumps(db, ensure_ascii=False, separators=(',', ':')))
