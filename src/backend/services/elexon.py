import logging
from datetime import datetime

from services.http_client import get_client

logger = logging.getLogger(__name__)


async def fetch_bmrs_generation():
    """
    BMRS - Balancing Mechanism Reporting Serice. This data is produced by Elexon,
    the organisaiton which runs the wholesale electricity market in the United Kingdom.
    This data only includes real time metered generation.
    """
    url = "https://data.elexon.co.uk/bmrs/api/v1/generation/outturn/summary"
    client = get_client()
    try:
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()
        bmrs_data = response.json()

        if not bmrs_data:
            return None, None, None

        times = [
            datetime.fromisoformat(d["startTime"].replace("Z", "+00:00"))
            for d in bmrs_data
        ]
        min_dt = min(times)
        max_dt = max(times)
        return bmrs_data, min_dt, max_dt
    except Exception as e:
        logger.error(f"Failed to fetch BMRS data: {e}")
        return None, None, None
