import json
import sys
from haversine import haversine, Unit

INFINITY_DIST = 1000000

with open('gtfs.json') as f:
  gtfs = json.load(f)
  gtfsRoutes = gtfs['routeList']
  gtfsStops = gtfs['stopList']

def isNameMatch(name_a, name_b):
    tmp_a = name_a.lower()
    tmp_b = name_b.lower()
    return tmp_a.find(tmp_b) >= 0 or tmp_b.find(tmp_a) >= 0

# nwfb, ctb routes only give list of stops in topological order
# the actual servicing routes may skip some stop in the coStops
# this DP function is trying to map the coStops back to GTFS stops
def matchStopsByDp ( coStops, gtfsStops, debug=False ):
  if len(gtfsStops) > len(coStops):
    return [], INFINITY_DIST
  # initialization
  sum = [[INFINITY_DIST for x in range(len(coStops)+1)  ] for y in range(len(gtfsStops)+1)]
  for j in range(len(coStops) - len(gtfsStops) + 1):
    sum[0][j] = 0

  # Perform DP
  for i in range(len(gtfsStops)):
    gtfsStop = gtfsStops[i]
    for j in range(len(coStops)):
      coStop = coStops[j]
      dist = haversine(
        (float(coStop['lat']), float(coStop['long'])),
        (gtfsStop['lat'], gtfsStop['lng'])
      ) * 1000

      sum[i+1][j+1] = min(
        sum[i][j] + dist, # from previous stops of both sides
        sum[i+1][j]       # skipping current coStops 
      )
  
  # fast return if no good result
  if not min(sum[len(gtfsStops)]) / len(gtfsStops) < 100:
    return [], INFINITY_DIST

  # backtracking
  i = len(gtfsStops)
  j = len(coStops)
  ret = []
  while i > 0 and j > 0:
    if sum[i][j] == sum[i][j-1]:
      j -= 1
    else:
      ret.append( ( i-1, j-1 ) )
      i -= 1
      j -= 1
  ret.reverse()

  return ret, min(sum[len(gtfsStops)]) / len(gtfsStops)

def matchRoutes(co):
  print (co)
  with open( 'routeList.%s.json' % co ) as f:
    routeList = json.load(f)
  with open( 'stopList.%s.json' % co ) as f:
    stopList = json.load(f)

  extraRoutes = []
  # one pass to find matches of co vs gtfs by DP
  for routeId, routeObj in gtfsRoutes.items():
    debug = False #routeObj['route'] in ['101'] and routeId == '1482'
    for bound, stops in routeObj['stops'].items():
      bestMatch = (-1, INFINITY_DIST)
      for route in routeList:
        if co in routeObj['co'] and route['route'] == routeObj['route']:
          ret, avgDist = matchStopsByDp([stopList[stop] for stop in route['stops']], [gtfsStops[stop] for stop in stops], debug)
          if avgDist < bestMatch[1]:
            bestMatch = (routeId, avgDist, ret, bound, stops, route)
      if bestMatch[1] < 100: # assume matching to be avg stop distance diff is lower than 100
        routeObj = gtfsRoutes[bestMatch[0]]
        ret, bound, stops, route = bestMatch[2:]
        if len(ret) == len(route['stops']) or len(ret) + 1 == len(route['stops']):
          if 'gtfs' in route:
            print(co, route['route'], 'matches multiple GTFS route', file=sys.stderr)
            route['freq'] = {**routeObj['freq'][bound], **route['freq']}
            route['co'] = routeObj['co']
            route['gtfs'].append(routeId)
          else:
            route['fares'] = [routeObj['fares'][bound][i] for i, j in ret[:-1]]
            route['freq'] = routeObj['freq'][bound]
            route['jt'] = routeObj['jt']
            route['co'] = routeObj['co']
            route['gtfs'] = [routeId]
        else:
          extra = route.copy()
          extra['stops'] = [route['stops'][j] for i, j in ret]
          extra['fares'] = [routeObj['fares'][bound][i] for i, j in ret[:-1]]
          extra['freq'] = routeObj['freq'][bound]
          extra['jt'] = routeObj['jt']
          extra['co'] = routeObj['co']
          extra['orig_tc'] = stopList[extra['stops'][0]]['name_tc']
          extra['orig_en'] = stopList[extra['stops'][0]]['name_en']
          extra['dest_tc'] = stopList[extra['stops'][-1]]['name_tc']
          extra['dest_en'] = stopList[extra['stops'][-1]]['name_en']
          extra['service_type'] = "2" if 'found' in route else "1"
          extra['gtfs'] = [routeId]
          route['found'] = True        # mark the route has mapped to GTFS, mainly for nwfb/ctb routes
          extraRoutes.append(extra)
        if '_route' not in routeObj:
          routeObj['_route'] = {}
        routeObj['_route'][co] = route.copy()
      elif co in routeObj['co']:
        print(co, routeObj['route'], 'cannot match any in GTFS')
    
  for route in routeList:
    if 'gtfs' not in route:
      route['co'] = [co]
      
  print (co, len([route for route in routeList if 'gtfs' not in route]), 'out of',len(routeList), 'not match')
  routeList.extend(extraRoutes)
  routeList = [route for route in routeList if 'found' not in route or 'fares' in route] # skipping routes that just partially mapped to GTFS
    
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