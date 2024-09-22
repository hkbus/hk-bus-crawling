from scipy.spatial import KDTree
import json
import math
import polars as pl

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    theta = math.atan2(y, x)
    
    return (math.degrees(theta) + 360) % 360

def group_bus_stops(bus_stops, max_distance=50, bearing_threshold=35):
    tree = KDTree(bus_stops.select("lat", "lng"))
    groups = pl.DataFrame(schema={"id":str, "lat":pl.Float64, "lng":pl.Float64, "name_en":str, "name_zh":str, "bus_group_id":pl.Int32})
    visited = set()
    group_id = 1

    print(len(bus_stops))
    
    for i in range(len(bus_stops)):
        if i in visited:
            continue

        # Create a new group for this stop
        stop1 = bus_stops[i]
        stop1 = stop1.with_columns(
            bus_group_id=group_id
        )
        group = stop1
        nearby_stop_indices = tree.query_ball_point([stop1['lat'][0], stop1['lng'][0]], r=max_distance/1000)
        
        for j in nearby_stop_indices:
            if i != j and j not in visited:
                stop2 = bus_stops[j]

                distance = haversine_distance(stop1['lat'][0], stop1['lng'][0], stop2['lat'][0], stop2['lng'][0])
                
                if distance <= max_distance:
                    if group.height > 1:
                        prev_stop = group[-2]
                        bearing1 = calculate_bearing(prev_stop['lat'][0], prev_stop['lng'][0], stop1['lat'][0], stop1['lng'][0])
                        bearing2 = calculate_bearing(stop1['lat'][0], stop1['lng'][0], stop2['lat'][0], stop2['lng'][0])
                        
                        if abs(bearing1 - bearing2) <= bearing_threshold or abs(bearing1 - bearing2) >= 360 - bearing_threshold:
                            stop2 = stop2.with_columns(
                                bus_group_id=group_id
                            )
                            group = group.vstack(stop2)
                    else:
                        stop2 = stop2.with_columns(
                            bus_group_id=group_id
                        )
                        group = group.vstack(stop2)
        
        group_id += 1
        visited.add(i)
        groups = groups.vstack(group)
    
    return groups

if __name__ == '__main__': 
    with open("routeFareList.min.json", 'r', encoding='utf8') as f:
        r = json.load(f)
        r = r['stopList']

    j2 = [{"id": id, "lat": v['location']['lat'], "lng": v['location']['lng'],
           "name_en": v['name']['en'], "name_zh": v['name']['zh']} for id, v in r.items()]

    df = pl.from_dicts(j2) #.lazy()
    #df = df.filter(pl.col('name_zh').str.contains('宋皇'))
    grouped_bus_stops = group_bus_stops(df)

    with open(f'groupBus_all.json', 'w', encoding='utf8') as f:
         f.write(grouped_bus_stops.write_json())