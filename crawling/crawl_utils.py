import httpx
import asyncio
import logging

logger=logging.getLogger(__name__)

async def emitRequest(url:str,client: httpx.AsyncClient):
  # retry if "Too many request (429)"
  while True:
    try:
      r = await client.get(url)
      if r.status_code == 200:
        return r
      elif r.status_code == 429 or r.status_code == 502:
        await asyncio.sleep(1)
      else:
        r.raise_for_status()
        raise Exception(r.status_code, url)
    except (httpx.PoolTimeout, httpx.ReadTimeout, httpx.ReadError) as e:
      logger.warning(f"Exception {repr(e)} occurred, retrying")
      await asyncio.sleep(1)
