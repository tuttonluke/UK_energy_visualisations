"""
===============================================================================
File: rte_france_energy.py
Description: Client for fetching energy data from RTE (France). https://www.rte-france.com/en/discover-rte/about-rte
Date: 2026-08-14
License: MIT License
===============================================================================
"""

import logging
from typing import Any, Dict, Optional

from services.http_client import get_client

from .base_energy_provider import BaseEnergyProvider, format_nested_data

logger = logging.getLogger(__name__)


class RteProvider(BaseEnergyProvider):
    """
    Provider for RTE / ODRE (France) API.
    """

    def __init__(self, energy_source: str):
        # Hardcode country to 'fr'
        super().__init__("fr", energy_source)

    def _map_source_name(self, source: str) -> str:
        mapping = {
            "solar": "solaire",
            "wind": "eolien",  # Need to verify exact field name on ODRE if wind is used
        }
        return mapping.get(source, source)

    async def _do_fetch(self) -> Optional[Dict[str, Any]]:
        source_field = self._map_source_name(self.energy_source)
        url = f"https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/eco2mix-regional-tr/records?limit=100&order_by=date_heure%20DESC&where={source_field}%20is%20not%20null"

        client = get_client()
        res = await client.get(url, timeout=10.0)
        res.raise_for_status()
        data = res.json()

        flat_data = {}
        latest_timestamp = None

        for record in data.get("results", []):
            insee_code = record.get("code_insee_region")
            gen = record.get(source_field)
            timestamp = record.get("date_heure")

            if insee_code and gen is not None and gen >= 0:
                # Keep only the most recent reading for each region
                if insee_code not in flat_data:
                    flat_data[insee_code] = gen
                if timestamp:
                    ts_formatted = timestamp.replace("+00:00", "Z")
                    if latest_timestamp is None or ts_formatted > latest_timestamp:
                        latest_timestamp = ts_formatted

        total_generation_mw = sum(flat_data.values())
        flat_data["totalGen"] = round(total_generation_mw, 1)
        if latest_timestamp:
            flat_data["timestamp"] = latest_timestamp

        return format_nested_data(flat_data, self.energy_source)
