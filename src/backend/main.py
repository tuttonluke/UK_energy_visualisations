"""
===============================================================================
File: main.py
Description: Entry point for the FastAPI application.
Date: 2026-08-14
License: MIT License
===============================================================================
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from rate_limiter import limiter
from routers import generation_router, river_levels_router, solar_router
from services.cache_store import CacheStore
from services.energy_providers.elexon_uk_bmrs import BMRSProvider
from services.energy_providers.elia_belgium_energy import EliaProvider
from services.energy_providers.energinet_denmark_energy import DenmarkProvider
from services.energy_providers.entsoe_energy import EntsoeProvider
from services.energy_providers.fraunhofer_energy_charts import EnergyChartsProvider
from services.energy_providers.neso_uk_energy import NesoProvider
from services.energy_providers.pvlive_uk_solar import PVLiveProvider
from services.energy_providers.rte_france_energy import RteProvider
from services.environment_providers.uk_environment_agency import (
    EnvironmentAgencyProvider,
)
from services.generation_aggregator import GenerationAggregator
from services.orchestrator import BackgroundOrchestrator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# --- Initialize Providers ---
pvlive_solar = PVLiveProvider("solar")
rte_solar = RteProvider("solar")

# For now, let's just initialize the stores.
solar_uk_store = CacheStore("solar_uk", pvlive_solar.fetch_live_data)
solar_fr_store = CacheStore("solar_fr", rte_solar.fetch_live_data)


async def fetch_all_energy_charts():
    countries = ["de", "nl", "at", "ch", "pl", "cz", "es", "pt"]
    results = {}
    for c in countries:
        try:
            provider = EnergyChartsProvider(c, "solar")
            data = await provider.fetch_live_data()
            if data is not None:
                results[c] = data
        except Exception as e:
            logger.error(f"Failed to fetch Energy-Charts data for {c}: {e}")
            results[c] = None
    return results


energy_charts_store = CacheStore("energy_charts", fetch_all_energy_charts)

denmark_solar = DenmarkProvider("solar")
solar_dk_store = CacheStore("solar_dk", denmark_solar.fetch_live_data)

elia_solar = EliaProvider("solar")
solar_be_store = CacheStore("solar_be", elia_solar.fetch_live_data)

italy_solar = EntsoeProvider(
    "it", "solar", ["IT_NORD", "IT_CNOR", "IT_CSUD", "IT_SUD", "IT_SICI", "IT_SARD"]
)
solar_it_store = CacheStore("solar_it", italy_solar.fetch_live_data)

ireland_solar = EntsoeProvider("ie", "solar", ["IE"])
solar_ie_store = CacheStore("solar_ie", ireland_solar.fetch_live_data)

ni_solar = EntsoeProvider("nie", "solar", ["NIE"])
solar_ni_store = CacheStore("solar_ni", ni_solar.fetch_live_data)

sweden_solar = EntsoeProvider(
    "se", "solar", {"SE1": "SE_1", "SE2": "SE_2", "SE3": "SE_3", "SE4": "SE_4"}
)
solar_se_store = CacheStore("solar_se", sweden_solar.fetch_live_data)

norway_solar = EntsoeProvider(
    "no",
    "solar",
    {"NO1": "NO_1", "NO2": "NO_2", "NO3": "NO_3", "NO4": "NO_4", "NO5": "NO_5"},
)
solar_no_store = CacheStore("solar_no", norway_solar.fetch_live_data)

# UK Generation Decoupled Data
bmrs_provider = BMRSProvider()
bmrs_store = CacheStore("bmrs", bmrs_provider.fetch_live_data)

neso_provider = NesoProvider()
neso_store = CacheStore("neso", neso_provider.fetch_live_data)

pvlive_history_store = CacheStore("pvlive_history", pvlive_solar.fetch_history)

# Generation plots
generation_aggregator = GenerationAggregator(
    bmrs_store, pvlive_history_store, neso_store
)
generation_store = CacheStore("generation", generation_aggregator.fetch_aggregated_data)

# Environment
ea_provider = EnvironmentAgencyProvider()
river_stations_store = CacheStore("river_stations", ea_provider.fetch_stations)
river_readings_store = CacheStore("river_readings", ea_provider.fetch_readings)

# --- Initialize Orchestrator ---
orchestrator = BackgroundOrchestrator()

# Solar
orchestrator.register("solar_uk", solar_uk_store.update, 900)
orchestrator.register("solar_fr", solar_fr_store.update, 900)
orchestrator.register("energy_charts", energy_charts_store.update, 900)
orchestrator.register("solar_dk", solar_dk_store.update, 900)
orchestrator.register("solar_be", solar_be_store.update, 900)
orchestrator.register("solar_it", solar_it_store.update, 900)
orchestrator.register("solar_ie", solar_ie_store.update, 900)
orchestrator.register("solar_ni", solar_ni_store.update, 900)
orchestrator.register("solar_se", solar_se_store.update, 900)
orchestrator.register("solar_no", solar_no_store.update, 900)

# UK Generation (Decoupled Fetches)
orchestrator.register("bmrs", bmrs_store.update, 900)
orchestrator.register("neso", neso_store.update, 900)
orchestrator.register("pvlive_history", pvlive_history_store.update, 900)

# Generation plots - polls fast as it only hits memory
orchestrator.register("generation", generation_store.update, 30)

# Environment
orchestrator.register("river_readings", river_readings_store.update, 900)
orchestrator.register("river_stations", river_stations_store.update, 86400)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application lifecycle.

    Startup:
    - Attaches CacheStores to app.state for dependency injection.
    - Starts the BackgroundOrchestrator to pre-fetch and periodically update data from external APIs.

    Shutdown:
    - Cancels background update tasks gracefully.
    - Closes the global HTTPX client connection pool.
    """
    from services.http_client import close_client

    app.state.solar_stores = {
        "uk": solar_uk_store,
        "france": solar_fr_store,
        "energy_charts": energy_charts_store,
        "denmark": solar_dk_store,
        "belgium": solar_be_store,
        "italy": solar_it_store,
        "ireland": solar_ie_store,
        "ni": solar_ni_store,
        "sweden": solar_se_store,
        "norway": solar_no_store,
    }
    app.state.generation_store = generation_store
    app.state.river_stations_store = river_stations_store
    app.state.river_readings_store = river_readings_store

    await orchestrator.start()
    try:
        yield
    finally:
        await orchestrator.stop()
        await close_client()


app = FastAPI(lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)


@app.middleware("http")
async def add_cache_control_header(request: Request, call_next):
    """
    Middleware that automatically injects Cache-Control headers into static file responses.
    This ensures browsers cache static assets (like large GeoJSON files) for 24 hours,
    reducing unnecessary bandwidth and improving load times.
    """
    try:
        response = await call_next(request)
        if (
            request.url.path.startswith("/static/")
            and "Cache-Control" not in response.headers
        ):
            response.headers["Cache-Control"] = "public, max-age=86400"
        return response
    except RuntimeError as exc:
        if str(exc) == "No response returned.":
            from fastapi import Response

            return Response(status_code=499)  # 499 Client Closed Request
        raise


# Serve static files (like GeoJSON) with compression support
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(solar_router.router, prefix="/api/solar", tags=["solar"])
app.include_router(
    generation_router.router, prefix="/api/generation", tags=["generation"]
)
app.include_router(
    river_levels_router.router, prefix="/api/environment", tags=["environment"]
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
