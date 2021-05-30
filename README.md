# HK Bus Crawling

This project is to fetch the bus route information of KMB, NWFB, CTB into one single JSON. It is daily synced to data.gov.hk and launched in gh-pages.

Command

`python ctb-nwfb.py && python kmb.py && python parseFare.py && python matchRoutes.py && python mergeRoutes.p`
