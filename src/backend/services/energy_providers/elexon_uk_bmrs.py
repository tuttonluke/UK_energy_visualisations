"""
===============================================================================
File: elexon_uk_bmrs.py
Description: Client for fetching UK generation data from Elexon BMRS. https://www.elexon.co.uk/
Date: 2026-08-14
License: MIT License
===============================================================================
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from services.energy_providers.base_energy_provider import BaseEnergyProvider
from services.http_client import get_client

logger = logging.getLogger(__name__)


class BMRSProvider(BaseEnergyProvider):
    """
    BMRS - Balancing Mechanism Reporting Serice. This data is produced by Elexon,
    the organisaiton which runs the wholesale electricity market in the United Kingdom.
    This data only includes real time metered generation.
    """

    def __init__(self):
        super().__init__("uk", "bmrs")
        self.url = "https://data.elexon.co.uk/bmrs/api/v1/generation/outturn/summary"

    async def _do_fetch(self) -> Optional[Dict[str, Any]]:
        client = get_client()
        response = await client.get(self.url, timeout=10.0)
        response.raise_for_status()
        bmrs_data = response.json()

        if not bmrs_data:
            return None

        times = [
            datetime.fromisoformat(d["startTime"].replace("Z", "+00:00"))
            for d in bmrs_data
        ]
        min_dt = min(times)
        max_dt = max(times)

        return {"data": bmrs_data, "min_dt": min_dt, "max_dt": max_dt}
