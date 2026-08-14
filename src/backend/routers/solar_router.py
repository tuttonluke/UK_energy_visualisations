"""
===============================================================================
File: solar_router.py
Description: API routes for fetching solar energy generation data from various providers.
Date: 2026-08-14
License: MIT License
===============================================================================
"""

from dependencies import get_solar_stores
from fastapi import APIRouter, Depends, HTTPException, Request
from rate_limiter import limiter

router = APIRouter()


@router.get("/")
@limiter.limit("60/minute")
async def get_all_solar_data(
    request: Request, solar_stores: dict = Depends(get_solar_stores)
):
    """
    Bulk endpoint to fetch all available solar data globally in a single request.
    Iterates over all active CacheStores and aggregates the results.
    """
    result = {}
    for country, store in solar_stores.items():
        data = await store.get()
        if data:
            result[country] = data

    if not result:
        raise HTTPException(
            status_code=503,
            detail="Solar data is currently unavailable globally. Please try again later.",
        )
    return result


@router.get("/{source_id}")
@limiter.limit("60/minute")
async def get_solar_source_data(
    request: Request, source_id: str, solar_stores: dict = Depends(get_solar_stores)
):
    """
    Dynamic endpoint to fetch solar data for a specific source/country ID.
    """
    if source_id not in solar_stores:
        raise HTTPException(
            status_code=404,
            detail=f"Solar source '{source_id}' is not configured.",
        )

    data = await solar_stores[source_id].get()
    if data is None:
        raise HTTPException(
            status_code=503,
            detail=f"Solar data for {source_id} is currently unavailable. Please try again later.",
        )
    return data
