import asyncio
import logging
from typing import Awaitable, Callable, Optional, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


class BaseDataProvider:
    """
    Abstract base class for all data providers (Energy, Environment, etc.).
    Provides a standardized mechanism for retries and error handling.
    """

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        # Maps cache keys to their last known good data to provide fallbacks on failure
        self._previous_data_cache = {}

    async def _execute_with_retry(
        self,
        fetch_func: Callable[..., Awaitable[T]],
        cache_key: str = "default",
        max_retries: int = 3,
        backoff: float = 2.0,
        *args,
        **kwargs,
    ) -> Optional[T]:
        """
        Executes a data fetching function with retries and a fallback to previous data.
        """
        for attempt in range(max_retries):
            try:
                data = await fetch_func(*args, **kwargs)
                if data:
                    self._previous_data_cache[cache_key] = data
                    return data
            except Exception as e:
                logger.warning(
                    f"Fetch failed for {self.provider_name} ({cache_key}) - "
                    f"Attempt {attempt + 1}/{max_retries}: {e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        f"All {max_retries} fetch attempts failed for {self.provider_name} ({cache_key})."
                    )

        # Fallback to previous data if all retries fail or if fetch_func returns None/empty
        previous_data = self._previous_data_cache.get(cache_key)
        if previous_data:
            logger.info(
                f"Falling back to previous data for {self.provider_name} ({cache_key})."
            )
            return previous_data

        return None
