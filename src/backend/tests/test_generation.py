from datetime import datetime
from unittest.mock import patch

import pytest


from services.cache_store import CacheStore
from services.generation_aggregator import GenerationAggregator


@patch("services.generation_aggregator.fetch_neso_embedded_wind")
@patch("services.generation_aggregator.fetch_pvlive_history")
@patch("services.generation_aggregator.fetch_bmrs_generation")
@pytest.mark.asyncio
async def test_generation_cache_update_and_merge(mock_bmrs, mock_pvlive, mock_neso):

    # Mock BMRS data
    mock_bmrs.return_value = (
        [
            {
                "startTime": "2026-07-08T12:00:00Z",
                "data": [
                    {"fuelType": "WIND", "generation": 1000},
                    {"fuelType": "SOLAR", "generation": 500},
                    {"fuelType": "CCGT", "generation": 2000},
                ],
            }
        ],
        datetime.fromisoformat("2026-07-08T12:00:00+00:00"),
        datetime.fromisoformat("2026-07-08T12:00:00+00:00"),
    )

    # Mock PVLive Data (key is end of period)
    mock_pvlive.return_value = {"2026-07-08T12:30:00Z": 300}

    # Mock NESO Data
    mock_neso.return_value = {"2026-07-08T12:30:00Z": 400}

    generation_store = CacheStore(
        "generation", GenerationAggregator.fetch_aggregated_data
    )
    await generation_store.update()

    # Verify the cache has been updated and merged
    data = await generation_store.get()
    assert isinstance(data, list)
    assert len(data) == 1

    period = data[0]
    assert period["startTime"] == "2026-07-08T12:00:00Z"

    # Find WIND and SOLAR
    wind_gen = next(
        item["generation"] for item in period["data"] if item["fuelType"] == "WIND"
    )
    solar_gen = next(
        item["generation"] for item in period["data"] if item["fuelType"] == "SOLAR"
    )

    # Original Wind: 1000 + Embedded: 400 = 1400
    assert wind_gen == 1400

    # Original Solar: 500 + Embedded: 300 = 800
    assert solar_gen == 800
