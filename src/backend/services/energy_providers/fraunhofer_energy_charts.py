import asyncio
import logging
from typing import Any, Dict, Optional

from services.http_client import get_client

from .base_energy_provider import BaseEnergyProvider, format_nested_data

logger = logging.getLogger(__name__)

# Global lock to prevent overlapping requests to Fraunhofer API
_ENERGY_CHARTS_LOCK = asyncio.Lock()


class EnergyChartsProvider(BaseEnergyProvider):
    """
    Provider for Fraunhofer Energy-Charts API.
    """

    def __init__(self, country: str, energy_source: str):
        super().__init__(country, energy_source)
        self._energy_charts_source_name = self._map_source_name(energy_source)

    def _map_source_name(self, source: str) -> str:
        mapping = {
            "solar": "Solar",
            "wind": "Wind onshore",
            "wind_offshore": "Wind offshore",
            "hydro": "Hydro",
        }
        return mapping.get(source, source.capitalize())

    async def _do_fetch(self) -> Optional[Dict[str, Any]]:
        client = get_client()
        url = f"https://api.energy-charts.info/public_power?country={self.country}"

        async with _ENERGY_CHARTS_LOCK:
            # Respect API rate limits - space out requests globally across all EnergyChartsProvider instances
            await asyncio.sleep(2.0)

            res = await client.get(url, timeout=15.0)
            res.raise_for_status()
            data = res.json()

        data_series = None
        unix_seconds_series = data.get("unix_seconds", [])

        for series in data.get("production_types", []):
            if series.get("name") == self._energy_charts_source_name:
                data_series = series.get("data", [])
                break

        if not data_series or not unix_seconds_series:
            logger.warning(
                f"Data for {self._energy_charts_source_name} not found in Energy-Charts response for {self.country}."
            )
            return None

        latest_value = 0
        latest_timestamp = None

        for j in range(len(data_series) - 1, -1, -1):
            val = data_series[j]
            if val is not None:
                latest_value = val
                if j < len(unix_seconds_series):
                    import datetime

                    latest_timestamp = datetime.datetime.fromtimestamp(
                        unix_seconds_series[j], tz=datetime.timezone.utc
                    ).isoformat()
                break

        flat_data = {"totalGen": round(latest_value, 1)}
        if latest_timestamp:
            flat_data["timestamp"] = latest_timestamp

        return format_nested_data(flat_data, self.energy_source)
