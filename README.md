# HK Bus Crawling

[![Python 3.8.8](https://img.shields.io/badge/python-3.8.8-blue.svg)](https://www.python.org/downloads/release/python-388/) ![Data fetching status](https://github.com/hkbus/hk-bus-crawling/actions/workflows/fetch-data.yml/badge.svg) 

This project is to fetch the bus route information of KMB, NWFB, CTB into one single JSON. It is daily synced to data.gov.hk and launched in gh-pages.

## Usage
Daily fetched JSON is in [gh-pages](https://github.com/hkbus/hk-bus-crawling/tree/gh-pages) or direct download [here](https://hkbus.github.io/hk-bus-crawling/routeFareList.min.json)

## Installation

To install the dependencies,
```
pip install -r requirements.txt
```

## Data Fetching

To fetch data, run the followings
```
python ctb-nwfb.py
python kmb.py
python nlb.py
python parseFare.py
python matchRoutes.py
python mergeRoutes.py
```

## Citing 

Please kindly state you are using this app as
`
HK Bus Crawling@2021, https://github.com/hkbus/hk-bus-crawling
`

## Contributors
[ChunLaw](http://github.com/chunlaw/)
