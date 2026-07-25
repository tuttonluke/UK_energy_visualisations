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
from services import quota_service
from services.cache_store import CacheStore
from services.environment_agency import fetch_ea_readings, fetch_ea_stations
from services.generation_aggregator import GenerationAggregator
from services.http_client import get_client
from services.orchestrator import BackgroundOrchestrator
from services.pvlive import fetch_pvlive_live
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

load_dotenv()

MAPBOX_ACCESS_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logging.getLogger("httpx").setLevel(logging.WARNING)


class EndpointFilter(logging.Filter):
    """
    Custom logging filter to suppress excessive Uvicorn access logs.
    Specifically targets and hides logs from the mapbox proxy endpoint,
    which can generate hundreds of entries per minute during normal map usage.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return "/api/proxy/mapbox" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

logger = logging.getLogger(__name__)


# Initialize Stores
solar_uk_store = CacheStore("solar_uk", fetch_pvlive_live)
generation_store = CacheStore("generation", GenerationAggregator.fetch_aggregated_data)
river_stations_store = CacheStore("river_stations", fetch_ea_stations)
river_readings_store = CacheStore("river_readings", fetch_ea_readings)

# Initialize Orchestrator
orchestrator = BackgroundOrchestrator()
orchestrator.register("solar_uk", solar_uk_store.update, 300)
orchestrator.register("generation", generation_store.update, 300)
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
    response = await call_next(request)
    if (
        request.url.path.startswith("/static/")
        and "Cache-Control" not in response.headers
    ):
        response.headers["Cache-Control"] = "public, max-age=86400"
    return response


# Serve static files (like GeoJSON) with compression support
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(solar.router, prefix="/api/solar", tags=["solar"])
app.include_router(generation.router, prefix="/api/generation", tags=["generation"])
app.include_router(river_levels.router, prefix="/api/environment", tags=["environment"])


# API endpoints
@app.get("/api/proxy/mapbox")
@limiter.limit("2000/minute")
async def proxy_mapbox(
    request: Request, path: str, client: httpx.AsyncClient = Depends(get_client)
):
    """
    Proxies requests to the Mapbox API to keep the access token hidden from the frontend.

    Features:
    - Prevents Server-Side Request Forgery (SSRF) by only accepting a 'path' parameter,
      forcing the base URL to always be https://api.mapbox.com.
    - Tracks API usage against a monthly quota to prevent billing surprises.
    - Uses HTTP streaming to efficiently pipe Mapbox tiles directly back to the client
      without loading them entirely into server memory first.
    """
    if not await quota_service.check_and_increment_quota():
        raise HTTPException(status_code=429, detail="Mapbox monthly quota exceeded")

    if not MAPBOX_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="Mapbox token not configured")

    base_url = httpx.URL("https://api.mapbox.com")
    params = dict(request.query_params)
    params.pop("path", None)
    params["access_token"] = MAPBOX_ACCESS_TOKEN
    new_url = base_url.copy_with(path=path, params=params)

    # Forward browser cache headers so Mapbox can return 304 Not Modified
    forward_headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() in ("if-none-match", "if-modified-since", "accept")
    }

    try:
        req = client.build_request("GET", new_url, headers=forward_headers)
        r = await client.send(req, stream=True)
    except httpx.HTTPError as e:
        logger.error(f"Mapbox proxy upstream error: {e}")
        raise HTTPException(status_code=502, detail="Failed to reach Mapbox") from e

    # Forward response headers, keeping content-encoding for raw passthrough
    headers = {}
    for k, v in r.headers.items():
        if k.lower() not in (
            "date",
            "server",
            "transfer-encoding",
            "connection",
            "content-length",
        ):
            headers[k] = v

    async def stream_and_close():
        try:
            async for chunk in r.aiter_raw():
                yield chunk
        finally:
            await r.aclose()

    return StreamingResponse(
        stream_and_close(),
        status_code=r.status_code,
        headers=headers,
        media_type=r.headers.get("content-type"),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
