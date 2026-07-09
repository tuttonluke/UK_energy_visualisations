import logging
import os
from contextlib import asynccontextmanager
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from rate_limiter import limiter
from routers import generation, river_levels, solar
from services import quota_service
from services.cache_manager import CacheManager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.types import ASGIApp, Message, Receive, Scope, Send

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logging.getLogger("httpx").setLevel(logging.WARNING)


class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/api/proxy/mapbox" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from services.http_client import close_client

    cache_manager = CacheManager()
    app.state.cache_manager = cache_manager
    await cache_manager.start_background_updates()
    try:
        yield
    finally:
        await cache_manager.stop_background_updates()
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


class CacheHeaderMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                path = scope.get("path", "")
                if path.startswith("/static/"):
                    headers = message.get("headers", [])
                    # Only append if no cache-control header already exists
                    if not any(k.lower() == b"cache-control" for k, _ in headers):
                        headers.append((b"cache-control", b"public, max-age=86400"))
                    message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


app.add_middleware(CacheHeaderMiddleware)

# Serve static files (like GeoJSON) with compression support
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(solar.router, prefix="/api/solar", tags=["solar"])
app.include_router(generation.router, prefix="/api/generation", tags=["generation"])
app.include_router(river_levels.router, prefix="/api/environment", tags=["environment"])


# API endpoints
@app.get("/api/proxy/mapbox")
@limiter.limit("500/minute")
async def proxy_mapbox(request: Request, url: str):
    if not await quota_service.check_and_increment_quota():
        raise HTTPException(status_code=429, detail="Mapbox monthly quota exceeded")

    parsed = urlparse(url)
    if parsed.netloc != "api.mapbox.com":
        raise HTTPException(status_code=400, detail="Invalid proxy URL")

    token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="Mapbox token not configured")

    query = parse_qs(parsed.query)
    query["access_token"] = [token]
    new_query = urlencode(query, doseq=True)
    new_url = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        )
    )

    # Use shared HTTP client for connection pooling
    from services.http_client import get_client

    client = get_client()

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
