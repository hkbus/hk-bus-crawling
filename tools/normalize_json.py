import json
import typer


def main(route_fare_list_json: str):
    """
    Simple tool to normalize the routeFareList.json for easier comparison. The normalized JSON will be written to the same directory with `.norm` added.
    """
    normalized_json_name = f"{route_fare_list_json}.norm"
    with open(route_fare_list_json) as f:
        route_fare_list = json.load(f)
    route_fare_list['holidays'] = sorted(route_fare_list['holidays'])

    with open(normalized_json_name, 'w') as f:
        json.dump(route_fare_list, f, sort_keys=True,
                  indent=4, ensure_ascii=False)


if __name__ == '__main__':
    typer.run(main)
