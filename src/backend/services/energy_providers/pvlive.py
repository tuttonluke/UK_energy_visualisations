import asyncio
import logging
from typing import Any, Dict, Optional

from services.http_client import get_client

from .base import BaseEnergyProvider, format_nested_data

logger = logging.getLogger(__name__)


async def fetch_pvlive_history(min_dt, max_dt):
    from datetime import timedelta

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


class PVLiveProvider(BaseEnergyProvider):
    """
    Provider for PV_Live (UK) API.
    """

    def __init__(self, energy_source: str):
        # Hardcode country to 'uk'
        super().__init__("uk", energy_source)

    async def fetch_pes_region_data(self, client, pes_id: int):
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

    async def _do_fetch(self) -> Optional[Dict[str, Any]]:
        if self.energy_source != "solar":
            logger.warning(
                f"PVLiveProvider only supports 'solar', got {self.energy_source}"
            )
            return None

        client = get_client()
        tasks = [self.fetch_pes_region_data(client, pes_id) for pes_id in range(10, 24)]
        results = await asyncio.gather(*tasks)

        flat_data = {}
        total_generation_mw = 0.0
        latest_timestamp = None

        for pes_id_str, generation, timestamp in results:
            if generation is not None and generation > 0:
                flat_data[pes_id_str] = generation
                total_generation_mw += generation
                if timestamp:
                    if latest_timestamp is None or timestamp > latest_timestamp:
                        latest_timestamp = timestamp

        flat_data["totalGen"] = round(total_generation_mw, 1)
        if latest_timestamp:
            flat_data["timestamp"] = latest_timestamp

        return format_nested_data(flat_data, self.energy_source)
