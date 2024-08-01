import httpx
import asyncio
import logging
import os

logger=logging.getLogger(__name__)

async def emitRequest(url:str,client: httpx.AsyncClient, headers={}):
  RETRY_TIMEOUT_MAX=60
  retry_timeout=1
  # retry if "Too many request (429)"
  while True:
    try:
      r = await client.get(url, headers=headers)
      if r.status_code == 200:
        return r
      elif r.status_code == 429 or r.status_code == 502:
        logger.warning(f"status_code={r.status_code}, wait {retry_timeout} and retry. URL={url}")
        await asyncio.sleep(retry_timeout)
        retry_timeout = min (retry_timeout * 2, RETRY_TIMEOUT_MAX)
      else:
        r.raise_for_status()
        raise Exception(r.status_code, url)
    except (httpx.PoolTimeout, httpx.ReadTimeout, httpx.ReadError) as e:
      logger.warning(f"Exception {repr(e)} occurred, wait {retry_timeout} and retry. URL={url}")
      await asyncio.sleep(retry_timeout)
      retry_timeout = min (retry_timeout * 2, RETRY_TIMEOUT_MAX)


def get_request_limit():
  default_limit = "4"
  return int(os.environ.get('REQUEST_LIMIT', default_limit))
