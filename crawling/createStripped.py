import json

with open('routeFareList.json', 'r', encoding="utf8") as read_file:
    data = json.load(read_file)

    route_list = data["routeList"]
    counter = 0
    route_keys = list(route_list.keys())
    for key in route_keys:
        route_data = route_list[key]
        del route_data["fares"]
        del route_data["faresHoliday"]
        del route_data["freq"]
        del route_data["jt"]
        del route_data["seq"]
        route_list[str(counter)] = route_data
        del route_list[key]
        counter += 1
    if "serviceDayMap" in data:
        del data["serviceDayMap"]
    del data["stopMap"]

    with open('routeFareList.strip.json', 'w', encoding="utf-8") as output_file:
        output_file.write(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
