# HK Bus Crawling (a.k.a. hk-bus-eta)

[![Python 3.8.8](https://img.shields.io/badge/python-3.8.8-blue.svg)](https://www.python.org/downloads/release/python-388/) ![Data fetching status](https://github.com/hkbus/hk-bus-crawling/actions/workflows/fetch-data.yml/badge.svg) 

This project is to fetch the bus route information of KMB, CTB, NLB, minibus, MTR, lightrail into one single JSON. It is daily synced to data.gov.hk and launched in gh-pages.

## Fetching Transport ETA

The package is a python vertion for the npm package [hk-bus-eta](https://www.npmjs.com/package/hk-bus-eta).

### Installation
To install the package,

```sh
pip install hk-bus-eta
```

## Usage

**Fetch ETAs of a route**
```python
from hk_bus_eta import HKEta

hketa = HKEta()
etas = hketa.getEtas(route_id = "TCL+1+Hong Kong+Tung Chung", seq=0, language="en")
print (etas)

"""
[{'eta': '2023-09-12T11:43:00+08:00', 'remark': {'zh': '1號月台', 'en': 'Platform 1'}, 'co': 'mtr'}, {'eta': '2023-09-12T11:51:00+08:00', 'remark': {'zh': '1號月台', 'en': 'Platform 1'}, 'co': 'mtr'}, {'eta': '2023-09-12T11:58:00+08:00', 'remark': {'zh': '1號月台', 'en': 'Platform 1'}, 'co': 'mtr'}, {'eta': '2023-09-12T12:05:00+08:00', 'remark': {'zh': '1號月台', 'en': 'Platform 1'}, 'co': 'mtr'}]
"""
```

**List Route IDs**
```python
from hk_bus_eta import HKEta

hketa = new HKEta()
route_ids = list( hketa.route_list.keys() )
print( route_ids )

"""
['1+1+CHUK YUEN ESTATE+STAR FERRY', '1+1+Central (Hong Kong Station Public Transport Interchange)+The Peak (Public Transport Terminus)', '1+1+Felix Villas+Happy Valley (Upper)', '1+1+Happy Valley (Upper)+Felix Villas', '1+1+Kowloon Bay (Telford Gardens)+Sai Kung', '1+1+Mui Wo Ferry Pier+Tai O', '1+1+STAR FERRY+CHUK YUEN ESTATE', '1+1+Sai Kung+Kowloon Bay (Telford Gardens)', '1+1+Tai O+Mui Wo Ferry Pier', '1+1+The Peak (Public Transport Terminus)+Central (Hong Kong Station Public Transport Interchange)']
"""
```


## Crawling by yourself

### Usage
Daily fetched JSON is in [gh-pages](https://github.com/hkbus/hk-bus-crawling/tree/gh-pages) or direct download [here](https://hkbus.github.io/hk-bus-crawling/routeFareList.min.json)

### Installation

To install the dependencies,
```
pip install -r ./crawling/requirements.txt
```

### Data Fetching

To fetch data, run the followings,
```
python ./crawling/parseHoliday.py
python ./crawling/ctb.py
python ./crawling/kmb.py
python ./crawling/nlb.py
python ./crawling/lrtfeeder.py
python ./crawling/lightRail.py
python ./crawling/mtr.py
python ./crawling/parseJourneyTime.py
python ./crawling/parseGtfs.py
python ./crawling/gmb.py
python ./crawling/matchGtfs.py
python ./crawling/cleansing.py
python ./crawling/mergeRoutes.py
```

## Citing 

Please kindly state you are using this app as
`
HK Bus Crawling@2021, https://github.com/hkbus/hk-bus-crawling
`

## Waypoint data

You may refer to the repository [HK Bus WayPoints Crawling](https://github.com/hkbus/route-waypoints)

## Contributors
[ChunLaw](http://github.com/chunlaw/)
