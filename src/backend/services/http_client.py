"""
===============================================================================
File: http_client.py
Description: Shared HTTP client configuration for external API requests.
Date: 2026-08-14
License: MIT License
===============================================================================
"""

import httpx

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        limits = httpx.Limits(max_connections=500, max_keepalive_connections=100)
        _client = httpx.AsyncClient(
            limits=limits, timeout=httpx.Timeout(15.0, connect=5.0)
        )
    return _client


async def close_client():
    global _client
    if _client:
        await _client.aclose()
        _client = None
