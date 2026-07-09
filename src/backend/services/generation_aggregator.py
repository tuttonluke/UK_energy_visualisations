import asyncio
import logging
from datetime import datetime, timedelta

from services.elexon import fetch_bmrs_generation
from services.neso import fetch_neso_embedded_wind
from services.pvlive import fetch_pvlive_history

logger = logging.getLogger(__name__)


class GenerationAggregator:
    @classmethod
    async def fetch_aggregated_data(cls):
        """
        Fetches generation data from BMRS and augments it with embedded wind (NESO)
        and solar generation (PVLive).
        """
        try:
            bmrs_data, pv_dict, neso_dict = await cls._fetch_all_data()
            if not bmrs_data:
                return None

            return cls._merge_data(bmrs_data, pv_dict, neso_dict)

        except Exception as e:
            logger.exception("Error aggregating generation data")
            return None

    @classmethod
    async def _fetch_all_data(cls):
        """Fetches primary and supplementary generation data concurrently."""
        bmrs_data, min_dt, max_dt = await fetch_bmrs_generation()
        if not bmrs_data:
            return None, {}, {}

        # Fetch supplementary data concurrently
        pv_task = fetch_pvlive_history(min_dt, max_dt)
        neso_task = fetch_neso_embedded_wind(min_dt)

        pv_dict, neso_dict = await asyncio.gather(pv_task, neso_task)
        return bmrs_data, pv_dict, neso_dict

    @classmethod
    def _merge_data(cls, bmrs_data, pv_dict, neso_dict):
        """Merges PV and NESO dictionary data into the BMRS periods."""
        for period in bmrs_data:
            start_dt = datetime.fromisoformat(
                period["startTime"].replace("Z", "+00:00")
            )
            end_dt = start_dt + timedelta(minutes=30)
            end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Inject Solar
            solar_gen = pv_dict.get(end_iso, 0)
            cls._inject_fuel_generation(period, "SOLAR", solar_gen)

            # Inject Embedded Wind
            wind_gen = neso_dict.get(end_iso, 0)
            cls._inject_fuel_generation(period, "WIND", wind_gen)

        return bmrs_data

    @classmethod
    def _inject_fuel_generation(cls, period, fuel_type, generation_amount):
        """Adds or updates a specific fuel type's generation within a period."""
        if generation_amount <= 0:
            return

        for item in period["data"]:
            if item["fuelType"] == fuel_type:
                item["generation"] += generation_amount
                return

        # If the fuel type wasn't already in the period, append it
        period["data"].append({"fuelType": fuel_type, "generation": generation_amount})
