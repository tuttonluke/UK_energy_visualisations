import logging
import os

import pandas as pd
from entsoe import EntsoePandasClient

logger = logging.getLogger(__name__)

async def fetch_ni_entsoe():
    """
    Fetches real-time solar generation for Northern Ireland (NIE)
    using the ENTSO-E Transparency Platform API.
    Note: ENTSO-E currently does not report Solar for NIE. 
    This service safely handles the missing column and returns 0 or None.
    """
    token = os.getenv("ENTSOE_TOKEN")
    if not token:
        logger.error("ENTSOE_TOKEN not found in environment")
        return None

    try:
        client = EntsoePandasClient(api_key=token)

        start = pd.Timestamp.utcnow() - pd.Timedelta(hours=2)
        end = pd.Timestamp.utcnow()

        ts = client.query_generation("NIE", start=start, end=end)
        
        data = {}
        val = 0.0

        if ts is not None and "Solar" in ts.columns:
            val = ts["Solar"].iloc[-1]
            if isinstance(val, pd.Series):
                val = val.iloc[-1]
            val = float(val)
            if pd.isna(val):
                val = 0.0
            data["totalGen"] = round(val, 1)
            return data
        
        # Northern Ireland doesn't report solar, so return None
        return None

    except Exception as e:
        logger.warning(f"ENTSO-E live fetch failed for Northern Ireland: {e}")
        return None
