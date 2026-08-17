"""
===============================================================================
File: energinet_denmark_energy.py
Description: Client for fetching energy data from Energinet (Denmark). https://en.energinet.dk/
Date: 2026-08-14
License: MIT License
===============================================================================
"""

import logging
from typing import Any, Dict, Optional

from services.http_client import get_client

from .base_energy_provider import BaseEnergyProvider, format_nested_data

logger = logging.getLogger(__name__)


class DenmarkProvider(BaseEnergyProvider):
    """
    Provider for Denmark (Energinet) API.
    """

    def __init__(self, energy_source: str):
        # Hardcode country to 'dk'
        super().__init__("dk", energy_source)

    def _map_source_name(self, source: str) -> str:
        mapping = {
            "solar": "SolarPower",
            "wind_onshore": "OnshoreWindPower",
            "wind_offshore": "OffshoreWindPower",
        }
        return mapping.get(source, "SolarPower")

    async def fetch_raw_data(self) -> Any:
        url = "https://api.energidataservice.dk/dataset/ElectricityProdex5MinRealtime?limit=10&sort=Minutes5UTC%20desc"
        client = get_client()

        res = await client.get(url, timeout=15.0)
        res.raise_for_status()
        return res.json()

    def extract_data(self, raw_data: Any) -> Optional[Dict[str, Any]]:
        if not raw_data:
            return None

        records = raw_data.get("records", [])
        source_field = self._map_source_name(self.energy_source)

        latest_dk1 = None
        latest_dk2 = None
        latest_timestamp = None

        for record in records:
            area = record.get("PriceArea")
            val = record.get(source_field)
            timestamp = record.get("Minutes5UTC")

            if val is not None:
                if area == "DK1" and latest_dk1 is None:
                    latest_dk1 = val
                elif area == "DK2" and latest_dk2 is None:
                    latest_dk2 = val

                if timestamp:
                    ts_formatted = (
                        timestamp + "Z" if not timestamp.endswith("Z") else timestamp
                    )
                    if latest_timestamp is None or ts_formatted > latest_timestamp:
                        latest_timestamp = ts_formatted

            if latest_dk1 is not None and latest_dk2 is not None:
                break

        if latest_dk1 is None and latest_dk2 is None:
            logger.warning(
                f"Denmark {self.energy_source} data not found in Energinet response."
            )
            return None

        dk1_val = latest_dk1 if latest_dk1 is not None else 0
        dk2_val = latest_dk2 if latest_dk2 is not None else 0

        total_gen = dk1_val + dk2_val

        flat_data = {
            "totalGen": round(total_gen, 1),
            "DK1": round(dk1_val, 1),
            "DK2": round(dk2_val, 1),
        }
        if latest_timestamp:
            flat_data["timestamp"] = latest_timestamp

        return format_nested_data(flat_data, self.energy_source)
