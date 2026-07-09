from typing import List

from fastapi import APIRouter, HTTPException, Request
from rate_limiter import limiter
from schemas import GenerationPeriod

router = APIRouter()


@router.get("/summary", response_model=List[GenerationPeriod])
@limiter.limit("60/minute")
async def get_generation_summary(request: Request):
    cache_manager = request.app.state.cache_manager
    data = await cache_manager.get_generation_summary()
    if data is None:
        raise HTTPException(
            status_code=503,
            detail="Generation data is currently unavailable. Please try again later.",
        )
    return data
