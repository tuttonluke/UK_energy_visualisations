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
