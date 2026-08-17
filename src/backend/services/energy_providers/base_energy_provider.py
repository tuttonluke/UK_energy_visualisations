"""
===============================================================================
File: base_energy_provider.py
Description: Base class for specific energy data provider implementations.
Date: 2026-08-14
License: MIT License
===============================================================================
"""

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

    async def _do_fetch(self) -> Optional[Dict[str, Any]]:
        """
        Template method that coordinates fetching and extracting data.
        """
        raw_data = await self.fetch_raw_data()
        if raw_data is None:
            return None

        return self.extract_data(raw_data)

    @abstractmethod
    async def fetch_raw_data(self) -> Any:
        """
        Network-bound method to execute HTTP requests and return the raw API response.
        """
        pass

    @abstractmethod
    def extract_data(self, raw_data: Any) -> Optional[Dict[str, Any]]:
        """
        CPU-bound method to parse the raw data and return a standardized flat dictionary.
        This method will be fully synchronous and extremely easy to unit test.
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
            nested[k] = {energy_source: None}
    return nested
