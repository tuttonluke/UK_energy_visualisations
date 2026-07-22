from typing import List

from dependencies import get_cache_manager
from fastapi import APIRouter, Depends, HTTPException, Request
from rate_limiter import limiter
from schemas import GenerationPeriod
from services.cache_manager import CacheManager

router = APIRouter()


@router.get("/summary", response_model=List[GenerationPeriod])
@limiter.limit("60/minute")
async def get_generation_summary(
    request: Request, cache_manager: CacheManager = Depends(get_cache_manager)
):
    data = await cache_manager.get_generation_summary()
    if data is None:
        raise HTTPException(
            status_code=503,
            detail="Generation data is currently unavailable. Please try again later.",
        )
    return data
