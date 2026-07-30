import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class BaseEnergyProvider(ABC):
    """
    Abstract base class for all energy data providers.
    Handles retries, rate limiting (optionally implemented by subclasses),
    and persistence of last known good data.
    """

    def __init__(self, country: str, energy_source: str):
        self.country = country
        self.energy_source = energy_source
        self._previous_data: Optional[Dict[str, Any]] = None

    @abstractmethod
    async def _do_fetch(self) -> Optional[Dict[str, Any]]:
        """
        Perform the actual data fetching and parsing.
        Should return a dictionary containing 'totalGen', 'timestamp', and region keys,
        where values are nested dicts: {'solar': 123.0}.
        Raises exceptions on network or HTTP errors.
        """
        pass

    async def fetch_live_data(
        self, max_retries: int = 3, backoff: float = 2.0
    ) -> Optional[Dict[str, Any]]:
        """
        Wraps the fetch logic with retries and fallback to previous data.
        """
        for attempt in range(max_retries):
            try:
                data = await self._do_fetch()
                if data:
                    self._previous_data = data
                    return data
            except Exception as e:
                logger.warning(
                    f"Fetch failed for {self.country} ({self.energy_source}) - Attempt {attempt + 1}/{max_retries}: {e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        f"All {max_retries} fetch attempts failed for {self.country} ({self.energy_source})."
                    )

        # Fallback to previous data if all retries fail or if _do_fetch returns None
        if self._previous_data:
            logger.info(
                f"Falling back to previous data for {self.country} ({self.energy_source})."
            )
            return self._previous_data

        return None


def format_nested_data(flat_data: Dict[str, Any], energy_source: str) -> Dict[str, Any]:
    """
    Helper function to convert a flat dict like:
    {'totalGen': 100, 'Region1': 50, 'timestamp': '...'}
    To:
    {'totalGen': {'solar': 100}, 'Region1': {'solar': 50}, 'timestamp': '...'}
    """
    if not flat_data:
        return flat_data

    nested = {}
    for k, v in flat_data.items():
        if k == "timestamp":
            nested[k] = v
        elif v is not None:
            nested[k] = {energy_source: v}
        else:
            nested[k] = {energy_source: 0.0}
    return nested
