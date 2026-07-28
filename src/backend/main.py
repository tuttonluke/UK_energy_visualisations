import logging
import os
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from rate_limiter import limiter
from routers import generation, river_levels, solar
from services.cache_store import CacheStore
from services.environment_agency import fetch_ea_readings, fetch_ea_stations
from services.generation_aggregator import GenerationAggregator
from services.http_client import get_client
from services.orchestrator import BackgroundOrchestrator
from services.solar_data.belgium_elia import fetch_belgium_live
from services.solar_data.denmark_energinet import fetch_denmark_live
from services.solar_data.energy_charts import fetch_energy_charts_live
from services.solar_data.france_rte import fetch_rte_live
from services.solar_data.uk_pvlive import fetch_pvlive_live
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# --- Initialize Stores ---
# Solar
solar_uk_store = CacheStore("solar_uk", fetch_pvlive_live)
solar_fr_store = CacheStore("solar_fr", fetch_rte_live)
solar_de_store = None  # Deprecated, use energy_charts_store
energy_charts_store = CacheStore("energy_charts", fetch_energy_charts_live)
solar_dk_store = CacheStore("solar_dk", fetch_denmark_live)
solar_be_store = CacheStore("solar_be", fetch_belgium_live)

# Generation plots
generation_store = CacheStore("generation", GenerationAggregator.fetch_aggregated_data)

# Environment
river_stations_store = CacheStore("river_stations", fetch_ea_stations)
river_readings_store = CacheStore("river_readings", fetch_ea_readings)

# --- Initialize Orchestrator ---
orchestrator = BackgroundOrchestrator()

# Solar
orchestrator.register("solar_uk", solar_uk_store.update, 300)
orchestrator.register("solar_fr", solar_fr_store.update, 300)
orchestrator.register("energy_charts", energy_charts_store.update, 300)
orchestrator.register("solar_dk", solar_dk_store.update, 300)
orchestrator.register("solar_be", solar_be_store.update, 300)

# Generation plots
orchestrator.register("generation", generation_store.update, 300)

# Environment
orchestrator.register("river_readings", river_readings_store.update, 300)
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

    app.state.solar_uk_store = solar_uk_store
    app.state.solar_fr_store = solar_fr_store
    app.state.energy_charts_store = energy_charts_store
    app.state.solar_dk_store = solar_dk_store
    app.state.solar_be_store = solar_be_store
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

app.include_router(solar.router, prefix="/api/solar", tags=["solar"])
app.include_router(generation.router, prefix="/api/generation", tags=["generation"])
app.include_router(river_levels.router, prefix="/api/environment", tags=["environment"])




if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
