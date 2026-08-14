"""
===============================================================================
File: generation_router.py
Description: API routes for fetching aggregated energy generation data.
Date: 2026-08-14
License: MIT License
===============================================================================
"""
from typing import List

from dependencies import get_generation_store
from fastapi import APIRouter, Depends, HTTPException, Request
from rate_limiter import limiter
from schemas import GenerationPeriod
from services.cache_store import CacheStore

router = APIRouter()


@router.get("/summary", response_model=List[GenerationPeriod])
@limiter.limit("60/minute")
async def get_generation(
    request: Request, generation_store: CacheStore = Depends(get_generation_store)
):
    data = await generation_store.get()
    if data is None:
        raise HTTPException(
            status_code=503,
            detail="Generation data is currently unavailable. Please try again later.",
        )
    return data
