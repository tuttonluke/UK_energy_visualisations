from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from main import app
from services.cache_manager import CacheManager


@pytest.fixture
def cache_manager():
    return CacheManager()


@pytest.fixture
def client():
    """Provides a TestClient with a mocked lifespan to prevent live API calls."""
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def test_lifespan(app_inst):
        # Initialize CacheManager without background updates
        app_inst.state.cache_manager = CacheManager()

        # Pre-populate cache so we don't hit live APIs or get 503s
        app_inst.state.cache_manager._cache["solar"] = {"totalGen": 100}
        app_inst.state.cache_manager._initialized["solar"] = True

        app_inst.state.cache_manager._cache["generation"] = [
            {"startTime": "2026-07-08T12:00:00Z", "data": []}
        ]
        app_inst.state.cache_manager._initialized["generation"] = True

        yield
        app_inst.state.cache_manager = None

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
        app_inst.state.cache_manager = CacheManager()
        # Do not pre-populate or mark initialized to simulate updater failure
        yield
        app_inst.state.cache_manager = None

    app.router.lifespan_context = test_lifespan
    with TestClient(app) as test_client:
        yield test_client
    app.router.lifespan_context = original_lifespan
