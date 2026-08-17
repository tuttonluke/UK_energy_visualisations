"""
===============================================================================
File: entsoe_energy.py
Description: Client for fetching energy data via the ENTSO-E API. https://www.entsoe.eu/data/transparency-platform/
ENTSOE is the European Network of Transmission System Operators for Electricity.
Date: 2026-08-14
License: MIT License
===============================================================================
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from entsoe import EntsoePandasClient

from .base_energy_provider import BaseEnergyProvider, format_nested_data

logger = logging.getLogger(__name__)


class EntsoeProvider(BaseEnergyProvider):
    """
    Base provider for ENTSO-E APIs.
    """

    def __init__(
        self, country: str, energy_source: str, zones: Union[List[str], Dict[str, str]]
    ):
        super().__init__(country, energy_source)
        if isinstance(zones, list):
            self.zones = {z: z for z in zones}
        else:
            self.zones = zones
        self._client = None
        self._entsoe_source_name = self._map_source_name(energy_source)

    def _get_client(self) -> EntsoePandasClient:
        if not self._client:
            token = os.getenv("ENTSOE_TOKEN")
            if not token:
                raise ValueError("ENTSOE_TOKEN not found in environment")
            self._client = EntsoePandasClient(api_key=token)
        return self._client

    def _map_source_name(self, source: str) -> str:
        mapping = {
            "solar": "Solar",
            "wind": "Wind Onshore",
            "wind_offshore": "Wind Offshore",
        }
        return mapping.get(source, source.capitalize())

    async def fetch_raw_data(self) -> Any:
        client = self._get_client()
        start = pd.Timestamp.now("UTC") - pd.Timedelta(hours=24)
        end = pd.Timestamp.now("UTC")

        raw_results = {}
        for out_zone, entsoe_zone in self.zones.items():
            try:
                # Run the synchronous API client query in a threadpool to prevent blocking the event loop
                ts = await asyncio.to_thread(
                    client.query_generation, entsoe_zone, start=start, end=end
                )
                raw_results[out_zone] = ts
            except Exception as e:
                logger.error(f"Error fetching {entsoe_zone} from ENTSO-E: {e}")
                raw_results[out_zone] = None

        return raw_results

    def extract_data(self, raw_data: Any) -> Optional[Dict[str, Any]]:
        if not raw_data:
            return None

        data = {}
        total = 0.0
        latest_timestamp = None

        for out_zone, ts in raw_data.items():
            if (
                ts is not None
                and not ts.empty
                and self._entsoe_source_name in ts.columns
            ):
                val = ts[self._entsoe_source_name].iloc[-1]
                idx = ts.index[-1]
                if isinstance(val, pd.Series):
                    val = val.iloc[0]
                val = float(val)

                if pd.isna(val):
                    val = 0.0

                data[out_zone] = val
                total += val

                if idx is not None:
                    ts_formatted = idx.isoformat()
                    if latest_timestamp is None or ts_formatted > latest_timestamp:
                        latest_timestamp = ts_formatted
            else:
                data[out_zone] = None

        if all(
            v is None for k, v in data.items() if k not in ["timestamp", "totalGen"]
        ):
            data["totalGen"] = None
        else:
            data["totalGen"] = total

        if latest_timestamp:
            data["timestamp"] = latest_timestamp

        if data.get("totalGen") == 0 and all(
            v == 0 or v is None for v in data.values() if isinstance(v, (int, float))
        ):
            logger.warning(
                f"No {self.energy_source} generation data found in ENTSO-E response for {self.country}."
            )

        return format_nested_data(data, self.energy_source)
