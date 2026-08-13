import copy
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class GenerationAggregator:
    def __init__(self, bmrs_store, pvlive_history_store, neso_store):
        """
        Takes references to CacheStores so it can pull data directly from memory
        without orchestrating network calls itself.
        """
        self.bmrs_store = bmrs_store
        self.pvlive_history_store = pvlive_history_store
        self.neso_store = neso_store

    async def fetch_aggregated_data(self):
        """
        Fetches generation data from BMRS and augments it with embedded wind (NESO)
        and solar generation (PVLive), using only cached data.
        """
        try:
            bmrs_cache = await self.bmrs_store.get()
            pv_dict = await self.pvlive_history_store.get()
            neso_dict = await self.neso_store.get()

            if not bmrs_cache or not bmrs_cache.get("data"):
                return None

            # Deep copy to avoid mutating the cached BMRS data shared with other endpoints
            bmrs_data = copy.deepcopy(bmrs_cache["data"])

            pv_dict = pv_dict or {}
            neso_dict = neso_dict or {}

            return self._merge_data(bmrs_data, pv_dict, neso_dict)

        except Exception:
            logger.exception("Error aggregating generation data")
            return None

    def _merge_data(self, bmrs_data, pv_dict, neso_dict):
        """Merges PV and NESO dictionary data into the BMRS periods."""
        for period in bmrs_data:
            start_dt = datetime.fromisoformat(
                period["startTime"].replace("Z", "+00:00")
            )
            end_dt = start_dt + timedelta(minutes=30)
            end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Inject Solar
            solar_gen = pv_dict.get(end_iso, 0)
            self._inject_fuel_generation(period, "SOLAR", solar_gen)

            # Inject Embedded Wind
            wind_gen = neso_dict.get(end_iso, 0)
            self._inject_fuel_generation(period, "WIND", wind_gen)

        return bmrs_data

    def _inject_fuel_generation(self, period, fuel_type, generation_amount):
        """Adds or updates a specific fuel type's generation within a period."""
        if generation_amount <= 0:
            return

        for item in period["data"]:
            if item["fuelType"] == fuel_type:
                item["generation"] += generation_amount
                return

        # If the fuel type wasn't already in the period, append it
        period["data"].append({"fuelType": fuel_type, "generation": generation_amount})
