import logging
from abc import abstractmethod
from typing import Any, Dict, Optional

from services.base_data_provider import BaseDataProvider

logger = logging.getLogger(__name__)


class BaseEnergyProvider(BaseDataProvider):
    """
    Abstract base class for all energy data providers.
    """

    def __init__(self, country: str, energy_source: str):
        super().__init__(f"{country}_{energy_source}")
        self.country = country
        self.energy_source = energy_source

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
        return await self._execute_with_retry(
            self._do_fetch,
            cache_key="live_data",
            max_retries=max_retries,
            backoff=backoff,
        )


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
