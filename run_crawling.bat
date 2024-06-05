@echo off

python ./crawling/parseHoliday.py pause
python ./crawling/ctb.py pause
python ./crawling/kmb.py pause
python ./crawling/nlb.py pause
python ./crawling/lrtfeeder.py pause
python ./crawling/lightRail.py pause
python ./crawling/mtr.py pause
python ./crawling/parseJourneyTime.py pause
python ./crawling/parseGtfs.py pause
python ./crawling/parseGtfsEn.py pause
python ./crawling/sunferry.py pause
python ./crawling/fortuneferry.py pause
python ./crawling/hkkf.py pause
python ./crawling/gmb.py pause
python ./crawling/matchGtfs.py pause
python ./crawling/cleansing.py pause
python ./crawling/mergeRoutes.py pause

