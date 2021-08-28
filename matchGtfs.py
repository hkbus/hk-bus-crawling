import json
import sys
from haversine import haversine, Unit

with open('gtfs.json') as f:
  gtfs = json.load(f)
  gtfsRoutes = gtfs['routeList']
  gtfsStops = gtfs['stopList']

def isNameMatch(name_a, name_b):
    tmp_a = name_a.lower()
    tmp_b = name_b.lower()
    return tmp_a.find(tmp_b) >= 0 or tmp_b.find(tmp_a) >= 0

def matchStops( coStops, gtfsStops, co, debug = False ):
  if debug: print(len(gtfsStops), len(coStops))
  if len(gtfsStops) > len(coStops) + 1:
    if debug:
      for i in range(len(gtfsStops)):
        print ( coStops[i]['name_tc'] if i < len(coStops) else ' - ', gtfsStops[i]['stopName'])
    return []
  ret = []
  idx = 0 
  for gtfsStop in gtfsStops:
    while idx < len(coStops):
      coStop = coStops[idx]
      dist = haversine(
        (float(coStop['lat']), float(coStop['long'])),
        (gtfsStop['lat'], gtfsStop['lng'])
      ) * 1000
      if debug: 
        print (idx+1, dist, isNameMatch(coStop['name_en'], gtfsStop['stopName'][co]), coStop['name_en'], gtfsStop['stopName'][co])
      if dist < 100 or ( isNameMatch(coStop['name_en'], gtfsStop['stopName'][co]) and dist < 500 ):
        ret.append(coStop)
        idx += 1
        break
      idx += 1
  if debug: print(len(ret), len(gtfsStops))
  if len(ret) == len(gtfsStops) or len(ret) == len(gtfsStops[:-1] if gtfsStops[0] == gtfsStops[-1] else gtfsStops):
    return ret
  return []

def matchRoutes(co):
  print (co)
  with open( 'routeList.%s.json' % co ) as f:
    routeList = json.load(f)
  with open( 'stopList.%s.json' % co ) as f:
    stopList = json.load(f)

  # first pass to find exact match co vs gtfs
  for route in routeList:
    for routeId, routeObj in gtfsRoutes.items():
      if co in routeObj['co'] and route['route'] == routeObj['route']:
        debug = False #route['route'] in ['107'] and routeId == '8468'
        if debug: print (routeId, routeObj['freq'])
        for bound, stops in routeObj['stops'].items():
          ret = matchStops([stopList[stop] for stop in route['stops']], [gtfsStops[stop] for stop in stops], co, debug)
          if len(ret) == len(route['stops']):
            if 'gtfs' in route:
              print(co, route['route'], 'matches multiple GTFS route', file=sys.stderr)
              route['freq'] = {**routeObj['freq'][bound], **route['freq']}
              route['co'] = routeObj['co']
              route['gtfs'].append(routeId)
            else:              
              route['fares'] = routeObj['fares'][bound]
              route['freq'] = routeObj['freq'][bound]
              route['co'] = routeObj['co']
              route['gtfs'] = [routeId]
            if '_route' not in routeObj:
              routeObj['_route'] = {}
            routeObj['_route'][co] = route.copy()
    if debug:
      print (route)
      print ()
      print ()
  
  extraRoutes = []
  # second pass to find partial match
  for routeId, routeObj in gtfsRoutes.items():
    if '_route' in routeObj and co in routeObj['_route']:
      continue
    for route in routeList:
      if co in routeObj['co'] and route['route'] == routeObj['route']:
        for bound, stops in routeObj['stops'].items():
          ret = matchStops([stopList[stop] for stop in route['stops']], [gtfsStops[stop] for stop in stops], co, debug)
          if len(ret) != 0:
            if len(ret) != len(route['stops']):
              extra = route.copy()
              extra['stops'] = [stop['stop'] for stop in ret]
              extra['fares'] = routeObj['fares'][bound]
              extra['freq'] = routeObj['freq'][bound]
              extra['co'] = routeObj['co']
              extra['orig_tc'] = ret[0]['name_tc']
              extra['orig_en'] = ret[0]['name_en']
              extra['dest_tc'] = ret[-1]['name_tc']
              extra['dest_en'] = ret[-1]['name_en']
              extra['service_type'] = "2"
              extra['gtfs'] = [routeId]
              if debug: print(len(ret), route['stops'])
              if '_route' not in routeObj:
                routeObj['_route'] = {}
              routeObj['_route'][co] = route.copy()
              extraRoutes.append(extra)

  for route in routeList:
    if 'gtfs' not in route:
      route['co'] = [co]
  print (co, len([route for route in routeList if 'gtfs' not in route]), 'out of',len(routeList), 'not match')
  routeList.extend(extraRoutes)
    
  with open( 'routeFareList.%s.json' % co, 'w' ) as f:
    f.write(json.dumps(routeList, ensure_ascii=False))
  
matchRoutes('kmb')
matchRoutes('nwfb')
matchRoutes('ctb')
matchRoutes('nlb')

'''
for routeId, route in gtfsRoutes.items():
  if '_route' not in route and route['co'][0] in ['nwfb', 'ctb', 'kmb', 'nlb']:
    print(routeId + ': ' + route['route'] + " " + route['orig']['zh'] + ' - ' + route['dest']['zh'] + ' not found')
'''

routeFareList = {}


with open( 'routeGtfs.all.json', 'w' ) as f:
  f.write(json.dumps(gtfsRoutes, ensure_ascii=False, indent=4))