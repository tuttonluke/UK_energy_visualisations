from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from main import app
from services.cache_store import CacheStore
from services.generation_aggregator import GenerationAggregator


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
        async def dummy_fetch():
            return {}

        solar_uk_store = CacheStore("solar_uk", dummy_fetch)
        solar_fr_store = CacheStore("solar_fr", dummy_fetch)
        energy_charts_store = CacheStore("energy_charts", dummy_fetch)
        solar_dk_store = CacheStore("solar_dk", dummy_fetch)
        solar_be_store = CacheStore("solar_be", dummy_fetch)

        app_inst.state.solar_stores = {
            "uk": solar_uk_store,
            "france": solar_fr_store,
            "energy_charts": energy_charts_store,
            "denmark": solar_dk_store,
            "belgium": solar_be_store,
        }

        app_inst.state.bmrs_store = CacheStore("bmrs", dummy_fetch)
        app_inst.state.neso_store = CacheStore("neso", dummy_fetch)
        app_inst.state.pvlive_history_store = CacheStore("pvlive_history", dummy_fetch)

        # GenerationAggregator now takes the stores
        app_inst.state.generation_store = CacheStore(
            "generation",
            GenerationAggregator(
                app_inst.state.bmrs_store,
                app_inst.state.pvlive_history_store,
                app_inst.state.neso_store,
            ).fetch_aggregated_data,
        )
        app_inst.state.river_stations_store = CacheStore("river_stations", dummy_fetch)
        app_inst.state.river_readings_store = CacheStore("river_readings", dummy_fetch)

        # Pre-populate cache so we don't hit live APIs or get 503s
        app_inst.state.solar_stores["uk"]._data = {"totalGen": {"solar": 100}}
        app_inst.state.solar_stores["uk"]._initialized = True

        app_inst.state.solar_stores["france"]._data = {
            "totalGen": {"solar": 50},
            "75": {"solar": 50},
        }
        app_inst.state.solar_stores["france"]._initialized = True

        app_inst.state.solar_stores["energy_charts"]._data = {
            "de": {"totalGen": {"solar": 120}},
            "nl": {"totalGen": {"solar": 80}},
        }
        app_inst.state.solar_stores["energy_charts"]._initialized = True

        app_inst.state.solar_stores["denmark"]._data = {"totalGen": {"solar": 30}}
        app_inst.state.solar_stores["denmark"]._initialized = True

        app_inst.state.solar_stores["belgium"]._data = {"totalGen": {"solar": 40}}
        app_inst.state.solar_stores["belgium"]._initialized = True

        app_inst.state.generation_store._data = [
            {"startTime": "2026-07-08T12:00:00Z", "data": []}
        ]
        app_inst.state.generation_store._initialized = True

        yield
        app_inst.state.solar_stores = {}
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
        async def dummy_fetch():
            return {}

        app_inst.state.solar_stores = {
            "uk": CacheStore("solar_uk", dummy_fetch),
            "france": CacheStore("solar_fr", dummy_fetch),
            "energy_charts": CacheStore("energy_charts", dummy_fetch),
            "denmark": CacheStore("solar_dk", dummy_fetch),
            "belgium": CacheStore("solar_be", dummy_fetch),
        }

        app_inst.state.bmrs_store = CacheStore("bmrs", dummy_fetch)
        app_inst.state.neso_store = CacheStore("neso", dummy_fetch)
        app_inst.state.pvlive_history_store = CacheStore("pvlive_history", dummy_fetch)

        app_inst.state.generation_store = CacheStore(
            "generation",
            GenerationAggregator(
                app_inst.state.bmrs_store,
                app_inst.state.pvlive_history_store,
                app_inst.state.neso_store,
            ).fetch_aggregated_data,
        )
        app_inst.state.river_stations_store = CacheStore("river_stations", dummy_fetch)
        app_inst.state.river_readings_store = CacheStore("river_readings", dummy_fetch)
        # Do not pre-populate or mark initialized to simulate updater failure
        yield
        app_inst.state.solar_stores = {}
        app_inst.state.generation_store = None
        app_inst.state.river_stations_store = None
        app_inst.state.river_readings_store = None

    app.router.lifespan_context = test_lifespan
    with TestClient(app) as test_client:
        yield test_client
    app.router.lifespan_context = original_lifespan
