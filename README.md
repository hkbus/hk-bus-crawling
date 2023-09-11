# HK Bus Crawling

[![Python 3.8.8](https://img.shields.io/badge/python-3.8.8-blue.svg)](https://www.python.org/downloads/release/python-388/) ![Data fetching status](https://github.com/hkbus/hk-bus-crawling/actions/workflows/fetch-data.yml/badge.svg) 

This project is to fetch the bus route information of KMB, CTB, minibus, MTR, lightrail into one single JSON. It is daily synced to data.gov.hk and launched in gh-pages.

## Usage
Daily fetched JSON is in [gh-pages](https://github.com/hkbus/hk-bus-crawling/tree/gh-pages) or direct download [here](https://hkbus.github.io/hk-bus-crawling/routeFareList.min.json)

## Installation

To install the dependencies,
```
pip install -r ./crawling/requirements.txt
```

## Data Fetching

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

## Contributors
[ChunLaw](http://github.com/chunlaw/)
