from unittest.mock import patch

import pytest


@patch("services.cache_manager.fetch_ea_stations")
@patch("services.cache_manager.fetch_ea_readings")
@pytest.mark.asyncio
async def test_river_levels_cache_update(mock_readings, mock_stations, cache_manager):
    mock_stations.return_value = {
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

    mock_readings.return_value = [{"measure": "http://measure/1", "value": 0.5}]

    await cache_manager.update_river_stations()
    await cache_manager.update_river_readings()

    stations = await cache_manager.get_river_stations()
    readings = await cache_manager.get_river_readings()

    assert "http://measure/1" in stations
    assert len(readings) == 1
    assert readings[0]["value"] == 0.5
