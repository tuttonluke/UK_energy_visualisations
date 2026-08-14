"""
===============================================================================
File: test_river_levels_router.py
Description: Tests for the river levels API router.
Date: 2026-08-14
License: MIT License
===============================================================================
"""

import pytest
from services.cache_store import CacheStore


@pytest.mark.asyncio
async def test_river_levels_cache_update():
    async def mock_fetch_stations():
        return {
            "http://measure/1": {
                "stationReference": "123",
                "label": "Test Station",
                "riverName": "Test River",
                "lat": 51.0,
                "long": -1.0,
                "typicalRangeLow": 0.1,
                "typicalRangeHigh": 1.0,
            }
        }

    async def mock_fetch_readings():
        return [{"measure": "http://measure/1", "value": 0.5}]

    stations_store = CacheStore("stations", mock_fetch_stations)
    readings_store = CacheStore("readings", mock_fetch_readings)

    await stations_store.update()
    await readings_store.update()

    stations = await stations_store.get()
    readings = await readings_store.get()

    assert "http://measure/1" in stations
    assert len(readings) == 1
    assert readings[0]["value"] == 0.5
