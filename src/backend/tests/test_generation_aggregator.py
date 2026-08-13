from datetime import datetime

import pytest
from services.cache_store import CacheStore
from services.generation_aggregator import GenerationAggregator


@pytest.mark.asyncio
async def test_generation_cache_update_and_merge():
    # Mock BMRS data CacheStore
    async def dummy_bmrs_fetch():
        return {
            "data": [
                {
                    "startTime": "2026-07-08T12:00:00Z",
                    "data": [
                        {"fuelType": "WIND", "generation": 1000},
                        {"fuelType": "SOLAR", "generation": 500},
                        {"fuelType": "CCGT", "generation": 2000},
                    ],
                }
            ],
            "min_dt": datetime.fromisoformat("2026-07-08T12:00:00+00:00"),
            "max_dt": datetime.fromisoformat("2026-07-08T12:00:00+00:00"),
        }

    bmrs_store = CacheStore("bmrs", dummy_bmrs_fetch)
    await bmrs_store.update()

    # Mock PVLive Data CacheStore (key is end of period)
    async def dummy_pvlive_fetch():
        return {"2026-07-08T12:30:00Z": 300}

    pvlive_store = CacheStore("pvlive", dummy_pvlive_fetch)
    await pvlive_store.update()

    # Mock NESO Data CacheStore
    async def dummy_neso_fetch():
        return {"2026-07-08T12:30:00Z": 400}

    neso_store = CacheStore("neso", dummy_neso_fetch)
    await neso_store.update()

    aggregator = GenerationAggregator(bmrs_store, pvlive_store, neso_store)
    generation_store = CacheStore("generation", aggregator.fetch_aggregated_data)
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
