import logging
import math
import json
import time
from haversine import haversine, Unit


def get_stop_group(
        route_list,
        stop_list,
        stop_seq_mapping,
        stop_list_grid,
        stop_id):
  DISTANCE_THRESHOLD = 50  # in metres
  BEARING_THRESHOLD = 45  # in degrees
  STOP_LIST_LIMIT = 50  # max number of stops in a group

  def get_stops_haversine_distance(stop_a, stop_b):
    if stop_a['location']['lat'] == stop_b['location']['lat'] and stop_a['location']['lng'] == stop_b['location']['lng']:
        return 0
    return haversine(
        (stop_a['location']['lat'], stop_a['location']['lng']),
        (stop_b['location']['lat'], stop_b['location']['lng']),
        unit=Unit.METERS  # specify that we want distance in meter, default is km
    )

  bearing_targets = stop_seq_mapping.get(stop_id, {}).get('bearings', [])

  def is_bearing_in_range(bearing):
    if BEARING_THRESHOLD >= 180 or not bearing_targets:
      return True
    for target in bearing_targets:
      bearing_min = target - BEARING_THRESHOLD
      bearing_max = target + BEARING_THRESHOLD
      if bearing_min < 0:
        bearing_min += 360
      if bearing_max > 360:
        bearing_max -= 360
      if (
          bearing_min <= bearing <= bearing_max or (
              bearing_min > bearing_max and (
                  bearing <= bearing_max or bearing >= bearing_min))):
        return True
    return False

  def search_nearby_stops(target_stop_id, excluded_stop_id_list):
    target_stop = stop_list[target_stop_id]
    # take lat/lng up to 3 decimal places, that's about 100m x 100m square
    lat = int(target_stop['location']['lat'] * 1000)
    lng = int(target_stop['location']['lng'] * 1000)

    nearby_stops = []
    for stop_id in stop_list_grid.get(f"{lat}_{lng}", []):
      if (stop_id not in excluded_stop_id_list and get_stops_haversine_distance(
              target_stop, stop_list[stop_id]) <= DISTANCE_THRESHOLD):
        bearings = stop_seq_mapping.get(stop_id, {}).get('bearings', [])
        if any(is_bearing_in_range(b) for b in bearings):
          nearby_stops.append({
              'id': stop_id,
              'co': stop_seq_mapping.get(stop_id, {}).get('co', '')
          })
    return nearby_stops

  stop_group = []
  stop_list_entries = search_nearby_stops(stop_id, [])

  # recursively search for nearby stops within thresholds (distance and bearing)
  # stop searching when no new stops are found within range, or when stop
  # list is getting too large
  i = 0
  while i < len(stop_list_entries):
    entry = stop_list_entries[i]
    stop_group.append([entry['co'], entry['id']])
    i += 1
    if len(stop_list_entries) < STOP_LIST_LIMIT:
      stop_list_entries.extend(
          search_nearby_stops(
              entry['id'], [
                  e['id'] for e in stop_list_entries]))

  # to reduce size of routeFareList.min.json, excl current stop_id from
  # final output stopMap
  return [stop for stop in stop_group if stop[1] != stop_id]
  # return stop_group


def get_bearing(a, b):
  φ1 = math.radians(a['lat'])
  φ2 = math.radians(b['lat'])
  λ1 = math.radians(a['lng'])
  λ2 = math.radians(b['lng'])

  y = math.sin(λ2 - λ1) * math.cos(φ2)
  x = (math.cos(φ1) * math.sin(φ2) -
       math.sin(φ1) * math.cos(φ2) * math.cos(λ2 - λ1))
  θ = math.atan2(y, x)
  brng = (math.degrees(θ) + 360) % 360  # in degrees
  return brng


def get_stop_bearings(route_stops):
  unique_routes = []
  bearings = []
  for route_stop in route_stops:
    if route_stop['bearing'] != -1:
      unique_route = f"{route_stop['co']}_{route_stop['routeKey'].split('+')[0]}_{route_stop['bearing']}"
      if unique_route not in unique_routes:
        unique_routes.append(unique_route)
        bearings.append(route_stop['bearing'])

  if not bearings:
    return []

  BEARING_THRESHOLD = 45  # in degrees
  BEARING_EPSILON = 10e-6  # very small number
  bearing_groups = []

  for bearing in bearings:
    if bearing == -1:
      continue
    if not bearing_groups:
      bearing_groups.append([bearing])
      continue

    for group in bearing_groups:
      if any(abs(b - bearing) < BEARING_EPSILON for b in group):
        break
      if any(
              abs(
                  b -
                  bearing) <= BEARING_THRESHOLD or abs(
                  b -
                  bearing) >= 360 -
              BEARING_THRESHOLD for b in group):
        group.append(bearing)
        break
    else:
      bearing_groups.append([bearing])

  if len(bearing_groups) == 1:
    return bearing_groups[0]

  longest_length = max(len(group) for group in bearing_groups)
  return [b for group in bearing_groups if len(
      group) == longest_length for b in group]

# Main function to process stops


def merge_stop_list():
  # Read the result from previous pipeline
  with open('routeFareList.mergeRoutes.min.json', 'r', encoding='UTF-8') as f:
    db = json.load(f)

  route_list = db['routeList']
  stop_list = db['stopList']
  start_time = time.time()
  stop_seq_mapping = {}

  # Preprocess the list of bearings for each stop
  for route_key, route_list_entry in route_list.items():
    stops = route_list_entry.get('stops', {})
    for co, co_stops in stops.items():
      for stop_pos, stop_id in enumerate(co_stops):
        if stop_id not in stop_seq_mapping:
          stop_seq_mapping[stop_id] = {
              "routeStops": [], "co": co, "bearings": []}
        if stop_pos == len(co_stops) - 1:
          stop_seq_mapping[stop_id]['routeStops'].append({
              'routeKey': route_key,
              'co': co,
              'seq': stop_pos,
              'bearing': -1
          })
        else:
          bearing = get_bearing(
              stop_list[stop_id]['location'], stop_list[co_stops[stop_pos + 1]]['location'])
          stop_seq_mapping[stop_id]['routeStops'].append({
              'routeKey': route_key,
              'co': co,
              'seq': stop_pos,
              'bearing': bearing
          })

  for stop_id in stop_seq_mapping.keys():
    stop_seq_mapping[stop_id]['bearings'] = get_stop_bearings(
        stop_seq_mapping[stop_id]['routeStops'])

  # Just dump the json in case of a need for trouble-shooting, but otherwise
  # we do not need this file
  with open('stopMap.routeStopsSequence.json', 'w', encoding='UTF-8') as f:
    json.dump(stop_seq_mapping, f)

  logger.info(
      f'Processed routeStopsSequence in {(time.time() - start_time) * 1000:.2f}ms')

  # Preprocess stopList, organise stops into ~100m x ~100m squares to reduce
  # size of nested loop later
  stop_list_grid = {}
  for stop_id, stop in stop_list.items():
    # take lat/lng up to 3 decimal places, that's about 100m x 100m square
    lat = int(stop['location']['lat'] * 1000)
    lng = int(stop['location']['lng'] * 1000)
    # add stop into the 9 grid boxes surrounding this stop
    grid = [
        f"{lat - 1}_{lng - 1}",
        f"{lat    }_{lng - 1}",
        f"{lat + 1}_{lng - 1}",
        f"{lat - 1}_{lng    }",
        f"{lat    }_{lng    }",
        f"{lat + 1}_{lng    }",
        f"{lat - 1}_{lng + 1}",
        f"{lat    }_{lng + 1}",
        f"{lat + 1}_{lng + 1}",
    ]
    for grid_id in grid:
      if grid_id not in stop_list_grid:
        stop_list_grid[grid_id] = []
      stop_list_grid[grid_id].append(stop_id)

  target_stop_list = list(stop_list.items())
  stop_map = {}
  count = 0
  group_count = 0

  for stop_id, stop in target_stop_list:
    count += 1
    # if count % 1000 == 0:
    #     logger.info(f"Processed {count} stops ({group_count} groups) at {(time.time() - start_time) * 1000:.2f}ms")

    stop_group = get_stop_group(
        route_list,
        stop_list,
        stop_seq_mapping,
        stop_list_grid,
        stop_id)
    if len(stop_group) > 0:
      group_count += 1
      stop_map[stop_id] = stop_group

  logger.info(
      f"Processed {count} stops ({group_count} groups) at {(time.time() - start_time) * 1000:.2f}ms")

  with open('stopMap.json', 'w', encoding='UTF-8') as f:
    json.dump(stop_map, f, indent=4)

  db['stopMap'] = stop_map

  with open('routeFareList.json', 'w', encoding='UTF-8') as f:
    json.dump(db, f, indent=4)

  # reduce size of routeFareList.min.json by rounding lat/lng values to 5 decimal places
  # 5 d.p. is roughly one-metre accuracy, it is good enough for this project
  # saves around 50kb in size for 14,000 stops
  for stop_id, stop in target_stop_list:
    stop_list[stop_id]['location']['lat'] = float(
        '%.5f' % (stop_list[stop_id]['location']['lat']))
    stop_list[stop_id]['location']['lng'] = float(
        '%.5f' % (stop_list[stop_id]['location']['lng']))

  db['stopList'] = stop_list

  logger.info(
      f"Reduced location lat/lng to 5 d.p. at {(time.time() - start_time) * 1000:.2f}ms")

  with open('routeFareList.alpha.json', 'w', encoding='UTF-8') as f:
    json.dump(db, f, indent=4)

  with open('routeFareList.min.json', 'w', encoding='UTF-8') as f:
    json.dump(db, f)

  with open('routeFareList.alpha.min.json', 'w', encoding='UTF-8') as f:
    json.dump(db, f)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  logger = logging.getLogger(__name__)
  merge_stop_list()
