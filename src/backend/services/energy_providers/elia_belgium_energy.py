import logging
from typing import Any, Dict, Optional

from services.http_client import get_client

from .base_energy_provider import BaseEnergyProvider, format_nested_data

logger = logging.getLogger(__name__)


class EliaProvider(BaseEnergyProvider):
    """
    Provider for Elia (Belgium) API.
    """

    def __init__(self, energy_source: str):
        # Hardcode country to 'be'
        super().__init__("be", energy_source)

    async def _do_fetch(self) -> Optional[Dict[str, Any]]:
        # Currently only supports Solar from ods087
        if self.energy_source != "solar":
            logger.warning(
                f"EliaProvider currently only supports 'solar', got {self.energy_source}"
            )
            return None

        url = "https://opendata.elia.be/api/explore/v2.1/catalog/datasets/ods087/records?limit=60&order_by=datetime%20desc&where=datetime%3C%3Dnow()"
        client = get_client()

        res = await client.get(url, timeout=15.0)
        res.raise_for_status()
        data = res.json()

        records = data.get("results", [])

        target_regions = ["Flanders", "Wallonia", "Brussels"]
        latest_vals = {}
        latest_timestamp = None

        for record in records:
            region = record.get("region")
            realtime = record.get("realtime")
            timestamp = record.get("datetime")

            val = realtime if realtime is not None else record.get("mostrecentforecast")

            if region in target_regions and region not in latest_vals:
                if val is not None:
                    latest_vals[region] = val
                    if timestamp:
                        ts_formatted = timestamp.replace("+00:00", "Z")
                        if latest_timestamp is None or ts_formatted > latest_timestamp:
                            latest_timestamp = ts_formatted

            if len(latest_vals) == len(target_regions):
                break

        region_map = {
            "Flanders": "Flanders",
            "Wallonia": "Région wallonne",
            "Brussels": "Brussels",
        }

        flat_data = {}
        total_gen = 0.0
        for r, val in latest_vals.items():
            topo_name = region_map.get(r, r)
            flat_data[topo_name] = round(val, 1)
            total_gen += val

        flat_data["totalGen"] = round(total_gen, 1)
        if latest_timestamp:
            flat_data["timestamp"] = latest_timestamp

        return format_nested_data(flat_data, self.energy_source)
