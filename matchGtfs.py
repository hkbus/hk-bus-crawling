import json
import sys
from haversine import haversine

INFINITY_DIST = 1000000
DIST_DIFF = 600

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
  if len(gtfsStops) > len(coStops) + 1:
    return [], INFINITY_DIST
  if len(gtfsStops) - len(coStops) == 1:
    gtfsStops = gtfsStops[:-1]
    
  # initialization
  distSum = [[INFINITY_DIST for x in range(len(coStops)+1)  ] for y in range(len(gtfsStops)+1)]
  for j in range(len(coStops) - len(gtfsStops) + 1):
    distSum[0][j] = 0

  # Perform DP
  for i in range(len(gtfsStops)):
    gtfsStop = gtfsStops[i]
    for j in range(len(coStops)):
      coStop = coStops[j]
      dist = haversine(
        (float(coStop['lat']), float(coStop['long'])),
        (gtfsStop['lat'], gtfsStop['lng'])
      ) * 1000

      distSum[i+1][j+1] = min(
        distSum[i][j] + dist, # from previous stops of both sides
        distSum[i+1][j]       # skipping current coStops 
      )

  # fast return if no good result
  if not min(distSum[len(gtfsStops)]) / len(gtfsStops) < DIST_DIFF:
    return [], INFINITY_DIST

  # backtracking
  i = len(gtfsStops)
  j = len(coStops)
  ret = []
  while i > 0 and j > 0:
    if distSum[i][j] == distSum[i][j-1]:
      j -= 1
    else:
      ret.append( ( i-1, j-1 ) )
      i -= 1
      j -= 1
  ret.reverse()
  
  # penalty distance is given for not exact match route
  penalty = sum([abs(a-b) for a, b in ret]) * 0.01
  
  return ret, min(distSum[len(gtfsStops)]) / len(gtfsStops) + penalty


def mergeRouteAsCircularRoute(routeA, routeB):
  return {
    "co": routeA['co'],
    "route": routeA["route"],
    "bound": routeA["bound"] + routeB["bound"],
    "orig_en": routeA["orig_en"],
    "orig_tc": routeA["orig_tc"],
    "dest_en": routeB["dest_en"],
    "dest_tc": routeB["dest_tc"],
    "serviceType": routeA["serviceType"],
    "stops": routeA['stops'] + routeB['stops']
  }

def getVirtualCircularRoutes(routeList, routeNo):
  indices = []
  for idx, route in enumerate(routeList):
    if route['route'] == routeNo:
      indices.append(idx)
  if len(indices) != 2:
    return []
  
  ret = []
  routeA = routeList[indices[0]]
  routeB = routeList[indices[1]]
  if "co" not in routeA or "serviceType" not in routeA:
    return []

  return [
    mergeRouteAsCircularRoute(routeA, routeB),
    mergeRouteAsCircularRoute(routeB, routeA)    
  ]

def printStopMatches(bestMatch, gtfsStops, stopList, co):
  stopPair = [(bestMatch[4][gtfsStopIdx], bestMatch[5]["stops"][routeStopIdx]) for gtfsStopIdx, routeStopIdx in bestMatch[2]]
  print (bestMatch[3], bestMatch[0], bestMatch[1])
  print ("\t|\t".join(["運輸處", co]))
  print ("\n".join([
    str(idx + 1) + "  " + "\t|\t".join(
      [gtfsStops[gtfsId]["stopName"][co], stopList[stopId]["name_tc"]]) for idx, (gtfsId, stopId) in enumerate(stopPair)]
    )
  )
  print ()

def matchRoutes(co):
  print (co)
  with open( 'routeList.%s.json' % co ) as f:
    routeList = json.load(f)
  with open( 'stopList.%s.json' % co ) as f:
    stopList = json.load(f)

  extraRoutes = []
  # one pass to find matches of co vs gtfs by DP
  for gtfsId, gtfsRoute in gtfsRoutes.items():
    debug = gtfsRoute['route'] == '85'
    if co == 'gmb' and co in gtfsRoute['co']: # handle for gmb
      for route in routeList:
        if route['gtfsId'] == gtfsId:
          route['fares'] = [gtfsRoute['fares']['1'][0] for i in range(len(route['stops'])-1) ]
    elif co in gtfsRoute['co']: # handle for other companies 
      for bound, stops in gtfsRoute['stops'].items():
        bestMatch = (-1, INFINITY_DIST)
        for route in routeList + getVirtualCircularRoutes(routeList, gtfsRoute['route']):
          if co in gtfsRoute['co'] and route['route'] == gtfsRoute['route']:
            ret, avgDist = matchStopsByDp([stopList[stop] for stop in route['stops']], [gtfsStops[stop] for stop in stops], debug)
            if avgDist < bestMatch[1]:
              bestMatch = (gtfsId, avgDist, ret, bound, stops, route)
        #if bestMatch[0] == -1:
        #  print (gtfsRoute['route'], getVirtualRoute(routeList, gtfsRoute['route']))
        # if debug:
        #   printStopMatches(bestMatch, gtfsStops, stopList, co)

        if bestMatch[1] < DIST_DIFF: # assume matching to be avg stop distance diff is lower than 100
          ret, bound, stops, route = bestMatch[2:]
          
          if (len(ret) == len(route['stops']) or len(ret) + 1 == len(route['stops'])) and 'gtfs' not in route:
            route['fares'] = [gtfsRoute['fares'][bound][i] for i, j in ret[:-1]]
            route['freq'] = gtfsRoute['freq'][bound]
            route['jt'] = gtfsRoute['jt']
            route['co'] = gtfsRoute['co']
            route['gtfs'] = [gtfsId]
          else:
            extra = route.copy()
            extra['stops'] = [route['stops'][j] for i, j in ret]
            extra['fares'] = [gtfsRoute['fares'][bound][i] for i, j in ret[:-1]]
            extra['freq'] = gtfsRoute['freq'][bound]
            extra['jt'] = gtfsRoute['jt']
            extra['co'] = gtfsRoute['co']
            extra['orig_tc'] = stopList[extra['stops'][0]]['name_tc']
            extra['orig_en'] = stopList[extra['stops'][0]]['name_en']
            extra['dest_tc'] = stopList[extra['stops'][-1]]['name_tc']
            extra['dest_en'] = stopList[extra['stops'][-1]]['name_en']
            extra['service_type'] = "2" if 'found' in route else "1"
            extra['gtfs'] = [gtfsId]
            route['found'] = True        # mark the route has mapped to GTFS, mainly for nwfb/ctb routes
            extraRoutes.append(extra)
          if '_route' not in gtfsRoute:
            gtfsRoute['_route'] = {}
          gtfsRoute['_route'][co] = route.copy()
        elif co in gtfsRoute['co']:
          print(co, gtfsRoute['route'], 'cannot match any in GTFS', file=sys.stderr)
    
  for route in routeList:
    if 'gtfs' not in route:
      route['co'] = [co]
      
  print (co, len([route for route in routeList if 'gtfs' not in route]), 'out of',len(routeList), 'not match')
  if co != 'mtr': routeList.extend(extraRoutes)
  routeList = [route for route in routeList if 'found' not in route or 'fares' in route] # skipping routes that just partially mapped to GTFS
    
  with open( 'routeFareList.%s.json' % co, 'w' ) as f:
    f.write(json.dumps(routeList, ensure_ascii=False))
  
matchRoutes('kmb')
matchRoutes('nwfb')
matchRoutes('ctb')
matchRoutes('nlb')
matchRoutes('lrtfeeder')
matchRoutes('gmb')
matchRoutes('lightRail')
matchRoutes('mtr')

'''
for routeId, route in gtfsRoutes.items():
  if '_route' not in route and route['co'][0] in ['nwfb', 'ctb', 'kmb', 'nlb']:
    print(routeId + ': ' + route['route'] + " " + route['orig']['zh'] + ' - ' + route['dest']['zh'] + ' not found')
'''

routeFareList = {}


with open( 'routeGtfs.all.json', 'w' ) as f:
  f.write(json.dumps(gtfsRoutes, ensure_ascii=False, indent=4))