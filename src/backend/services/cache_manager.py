import asyncio
import logging

from services.environment_agency import fetch_ea_readings, fetch_ea_stations
from services.pvlive import fetch_pvlive_live

logger = logging.getLogger(__name__)


class CacheManager:
    def __init__(self):
        # In-memory store
        self._cache = {
            "generation": [],
            "solar": {"total_gen": 0},
            "river_stations": {},
            "river_readings": [],
        }
        self._initialized = {
            "generation": False,
            "solar": False,
            "river_stations": False,
            "river_readings": False,
        }
        self._locks = {
            "generation": asyncio.Lock(),
            "solar": asyncio.Lock(),
            "river_stations": asyncio.Lock(),
            "river_readings": asyncio.Lock(),
        }
        self._updater_task = None

    async def start_background_updates(self):
        """Starts the background loop to proactively update caches."""
        self._updater_task = asyncio.create_task(self._background_updater())

    async def stop_background_updates(self):
        if self._updater_task:
            self._updater_task.cancel()
            try:
                await self._updater_task
            except asyncio.CancelledError:
                pass

    async def _background_updater(self):
        logger.info("Background data fetcher started.")
        await self.update_river_stations()

        stations_timer = 0
        while True:
            try:
                # Fetch these every 5 minutes
                await asyncio.gather(
                    self.update_generation(),
                    self.update_solar(),
                    self.update_river_readings(),
                )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("Error in background fetch loop")

            # Wait 5 minutes
            await asyncio.sleep(300)
            stations_timer += 300

            # Update stations every 24 hours (86400 seconds)
            if stations_timer >= 86400:
                await self.update_river_stations()
                stations_timer = 0

    # Getters
    async def get_generation_summary(self):
        if not self._initialized["generation"]:
            return None
        return self._cache["generation"]

    async def get_solar(self):
        if not self._initialized["solar"]:
            return None
        return self._cache["solar"]

    async def get_river_stations(self):
        if not self._initialized["river_stations"]:
            return None
        return self._cache["river_stations"]

    async def get_river_readings(self):
        if not self._initialized["river_readings"]:
            return None
        return self._cache["river_readings"]

    # Updaters
    async def update_generation(self):
        async with self._locks["generation"]:
            try:
                from services.generation_aggregator import GenerationAggregator

                aggregated_data = await GenerationAggregator.fetch_aggregated_data()
                if aggregated_data:
                    self._cache["generation"] = aggregated_data
                    self._initialized["generation"] = True
                    logger.info("Generation cache updated.")
            except Exception as e:
                logger.exception("Error updating generation cache")

    async def update_solar(self):
        async with self._locks["solar"]:
            try:
                data = await fetch_pvlive_live()
                if data:
                    self._cache["solar"] = data
                    self._initialized["solar"] = True
                    logger.info("Solar cache updated.")
            except Exception as e:
                logger.exception("Error updating solar cache")

    async def update_river_stations(self):
        async with self._locks["river_stations"]:
            try:
                stations = await fetch_ea_stations()
                if stations:
                    self._cache["river_stations"] = stations
                    self._initialized["river_stations"] = True
                    logger.info(f"River stations cache updated ({len(stations)}).")
            except Exception as e:
                logger.exception("Error updating river stations cache")

    async def update_river_readings(self):
        async with self._locks["river_readings"]:
            try:
                readings = await fetch_ea_readings()
                if readings:
                    self._cache["river_readings"] = readings
                    self._initialized["river_readings"] = True
                    logger.info(f"River readings cache updated ({len(readings)}).")
            except Exception as e:
                logger.exception("Error updating river readings cache")
