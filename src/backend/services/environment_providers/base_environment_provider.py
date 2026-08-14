"""
===============================================================================
File: base_environment_provider.py
Description: Base class for specific environmental data provider implementations.
Date: 2026-08-14
License: MIT License
===============================================================================
"""
import logging

from services.base_data_provider import BaseDataProvider

logger = logging.getLogger(__name__)


class BaseEnvironmentProvider(BaseDataProvider):
    """
    Abstract base class for all environmental data providers.
    Inherits retry and fallback mechanisms from BaseDataProvider.
    """

    def __init__(self, provider_name: str):
        super().__init__(provider_name)
