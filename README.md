# HK Bus Crawling

This project is to fetch the bus route information of KMB, NWFB, CTB into one single JSON. It is daily synced to data.gov.hk and launched in gh-pages.

## Usage
Daily fetched JSON is in gh-pages or [https://hkbus.github.io/hk-bus-crawling/routeFareList.json]

## Command

`python ctb-nwfb.py && python kmb.py && python parseFare.py && python matchRoutes.py && python mergeRoutes.py`

## Citing 

Please kindly state you are using this app as
`
HK Bus Crawling
(https://github.com/hkbus/hk-bus-crawling)[https://github.com/hkbus/hk-bus-crawling]
`

