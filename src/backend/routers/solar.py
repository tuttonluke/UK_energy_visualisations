from fastapi import APIRouter, HTTPException, Request
from rate_limiter import limiter
from schemas import SolarResponse

router = APIRouter()


@router.get("/solar", response_model=SolarResponse)
@limiter.limit("60/minute")
async def get_solar(request: Request):
    cache_manager = request.app.state.cache_manager
    data = await cache_manager.get_solar()
    if data is None:
        raise HTTPException(
            status_code=503,
            detail="Solar data is currently unavailable. Please try again later.",
        )
    return data
