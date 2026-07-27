from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from main import app
from services.cache_store import CacheStore
from services.environment_agency import fetch_ea_readings, fetch_ea_stations
from services.generation_aggregator import GenerationAggregator
from services.solar_data.france_rte import fetch_rte_live
from services.solar_data.uk_pvlive import fetch_pvlive_live
from services.solar_data.energy_charts import fetch_energy_charts_live
from services.solar_data.belgium_elia import fetch_belgium_live
from services.solar_data.denmark_energinet import fetch_denmark_live


@pytest.fixture
def cache_store():
    # Helper for generic CacheStore testing
    async def dummy_fetch():
        return {}

    return CacheStore("dummy", dummy_fetch)


@pytest.fixture
def client():
    """Provides a TestClient with a mocked lifespan to prevent live API calls."""
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def test_lifespan(app_inst):
        # Initialize CacheStores without background updates
        app_inst.state.solar_uk_store = CacheStore("solar_uk", fetch_pvlive_live)
        app_inst.state.solar_fr_store = CacheStore("solar_fr", fetch_rte_live)
        app_inst.state.energy_charts_store = CacheStore("energy_charts", fetch_energy_charts_live)
        app_inst.state.solar_dk_store = CacheStore("solar_dk", fetch_denmark_live)
        app_inst.state.solar_be_store = CacheStore("solar_be", fetch_belgium_live)
        app_inst.state.generation_store = CacheStore(
            "generation", GenerationAggregator.fetch_aggregated_data
        )
        app_inst.state.river_stations_store = CacheStore(
            "river_stations", fetch_ea_stations
        )
        app_inst.state.river_readings_store = CacheStore(
            "river_readings", fetch_ea_readings
        )

        # Pre-populate cache so we don't hit live APIs or get 503s
        app_inst.state.solar_uk_store._data = {"totalGen": 100}
        app_inst.state.solar_uk_store._initialized = True

        app_inst.state.solar_fr_store._data = {"totalGen": 50, "75": 50}
        app_inst.state.solar_fr_store._initialized = True

        app_inst.state.energy_charts_store._data = {"de": {"totalGen": 120}, "nl": {"totalGen": 80}}
        app_inst.state.energy_charts_store._initialized = True

        app_inst.state.solar_dk_store._data = {"totalGen": 30}
        app_inst.state.solar_dk_store._initialized = True

        app_inst.state.solar_be_store._data = {"totalGen": 40}
        app_inst.state.solar_be_store._initialized = True

        app_inst.state.generation_store._data = [
            {"startTime": "2026-07-08T12:00:00Z", "data": []}
        ]
        app_inst.state.generation_store._initialized = True

        yield
        app_inst.state.solar_uk_store = None
        app_inst.state.solar_fr_store = None
        app_inst.state.energy_charts_store = None
        app_inst.state.solar_dk_store = None
        app_inst.state.solar_be_store = None
        app_inst.state.generation_store = None
        app_inst.state.river_stations_store = None
        app_inst.state.river_readings_store = None

    app.router.lifespan_context = test_lifespan
    with TestClient(app) as test_client:
        yield test_client
    app.router.lifespan_context = original_lifespan


@pytest.fixture
def empty_client():
    """Provides a TestClient with an empty cache to test 503 scenarios."""
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def test_lifespan(app_inst):
        app_inst.state.solar_uk_store = CacheStore("solar_uk", fetch_pvlive_live)
        app_inst.state.solar_fr_store = CacheStore("solar_fr", fetch_rte_live)
        app_inst.state.energy_charts_store = CacheStore("energy_charts", fetch_energy_charts_live)
        app_inst.state.solar_dk_store = CacheStore("solar_dk", fetch_denmark_live)
        app_inst.state.solar_be_store = CacheStore("solar_be", fetch_belgium_live)
        app_inst.state.generation_store = CacheStore(
            "generation", GenerationAggregator.fetch_aggregated_data
        )
        app_inst.state.river_stations_store = CacheStore(
            "river_stations", fetch_ea_stations
        )
        app_inst.state.river_readings_store = CacheStore(
            "river_readings", fetch_ea_readings
        )
        # Do not pre-populate or mark initialized to simulate updater failure
        yield
        app_inst.state.solar_uk_store = None
        app_inst.state.solar_fr_store = None
        app_inst.state.energy_charts_store = None
        app_inst.state.solar_dk_store = None
        app_inst.state.solar_be_store = None
        app_inst.state.generation_store = None
        app_inst.state.river_stations_store = None
        app_inst.state.river_readings_store = None

    app.router.lifespan_context = test_lifespan
    with TestClient(app) as test_client:
        yield test_client
    app.router.lifespan_context = original_lifespan
