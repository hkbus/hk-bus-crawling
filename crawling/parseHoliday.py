import json
import logging
from os import path

import httpx
import asyncio

logger = logging.getLogger(__name__)

async def main():
  if not path.isfile('holiday.json'):
    async with httpx.AsyncClient() as a_client:
      r = await a_client.get('https://www.1823.gov.hk/common/ical/tc.json')
      data = r.json()
    with open('holiday.json', 'w') as f:
      json.dump([holiday['dtstart'][0]
                for holiday in data['vcalendar'][0]['vevent']], f)
    logger.info('Created holiday.json')
  else:
    logger.info('holiday.json already exist, download skipped')

if __name__=='__main__':
  logging.basicConfig(level=logging.INFO)
  asyncio.run(main())