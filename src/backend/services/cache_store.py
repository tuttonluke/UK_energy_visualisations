"""
===============================================================================
File: cache_store.py
Description: In-memory thread-safe cache storage for managing fetched API data.
Date: 2026-08-14
License: MIT License
===============================================================================
"""

import asyncio
import logging
from typing import Awaitable, Callable, Generic, Optional, TypeVar

T = TypeVar("T")


class CacheStore(Generic[T]):
    """
    A generic thread-safe cache store that automatically manages state, locking,
    and initialization for any given asynchronous fetch function.
    """

    def __init__(self, name: str, fetch_func: Callable[[], Awaitable[T]]):
        self.name = name
        self.fetch_func = fetch_func
        self._data: Optional[T] = None
        self._lock = asyncio.Lock()
        self._initialized = False
        self.logger = logging.getLogger(f"CacheStore.{name}")

    async def get(self) -> Optional[T]:
        """Returns the cached data if it has been initialized, otherwise None."""
        if not self._initialized:
            return None
        return self._data

    async def update(self):
        """Fetches new data and updates the cache in a thread-safe manner."""
        async with self._lock:
            try:
                data = await self.fetch_func()
                if data is not None:
                    self._data = data
                    self._initialized = True
                    self.logger.info("Cache updated successfully.")
            except Exception:
                self.logger.exception("Error updating cache")
