import asyncio
import logging
from datetime import timedelta

from services.http_client import get_client

logger = logging.getLogger(__name__)


async def fetch_pvlive_history(min_dt, max_dt):
    start_str = min_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_dt = max_dt + timedelta(minutes=60)
    end_str = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    url = f"https://api.pvlive.uk/pvlive/api/v4/pes/0?start={start_str}&end={end_str}"
    client = get_client()
    try:
        res = await client.get(url, timeout=10.0)
        res.raise_for_status()
        data = res.json()

        pv_dict = {}
        for row in data.get("data", []):
            pv_dict[row[1]] = row[2]
        return pv_dict
    except Exception as e:
        logger.error(f"PVLive history fetch failed: {e}")
        return {}


async def fetch_pes_region_data(client, pes_id: int):
    url = f"https://api.pvlive.uk/pvlive/api/v4/pes/{pes_id}"
    try:
        response = await client.get(url, timeout=5.0)
        response.raise_for_status()
        data = response.json()

        if data.get("data") and len(data["data"]) > 0:
            return str(pes_id), data["data"][0][2], data["data"][0][1]
    except Exception as e:
        logger.error(f"Failed to fetch data for PES {pes_id}: {e}")

    return str(pes_id), 0, None


async def fetch_pvlive_live():
    try:
        new_data = {}
        total_generation_mw = 0
        latest_timestamp = None

        client = get_client()
        tasks = [fetch_pes_region_data(client, pes_id) for pes_id in range(10, 24)]
        results = await asyncio.gather(*tasks)

        for pes_id_str, generation, timestamp in results:
            if generation is not None and generation > 0:
                new_data[pes_id_str] = generation
                total_generation_mw += generation
                if timestamp:
                    if latest_timestamp is None or timestamp > latest_timestamp:
                        latest_timestamp = timestamp

        new_data["totalGen"] = round(total_generation_mw, 1)
        if latest_timestamp:
            new_data["timestamp"] = latest_timestamp
        return new_data
    except Exception as e:
        logger.error(f"PVLive live fetch completely failed: {e}")
        return None
