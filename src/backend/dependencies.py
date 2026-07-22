from fastapi import Request
from services.cache_manager import CacheManager


def get_cache_manager(request: Request) -> CacheManager:
    return request.app.state.cache_manager
