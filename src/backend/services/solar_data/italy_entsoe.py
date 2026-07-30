import logging
import os

import pandas as pd
from entsoe import EntsoePandasClient

logger = logging.getLogger(__name__)

# Terna Bidding Zones
ZONES = ["IT_NORD", "IT_CNOR", "IT_CSUD", "IT_SUD", "IT_SICI", "IT_SARD"]


async def fetch_italy_entsoe():
    """
    Fetches real-time solar generation for Italy's 6 macro bidding zones
    using the ENTSO-E Transparency Platform API.
    Returns a dictionary mapping Bidding Zone to MW, plus 'totalGen'.
    """
    token = os.getenv("ENTSOE_TOKEN")
    if not token:
        logger.error("ENTSOE_TOKEN not found in environment")
        return None

    try:
        client = EntsoePandasClient(api_key=token)

        # We query the last 24 hours to ensure we get the latest data point even if delayed
        start = pd.Timestamp.utcnow() - pd.Timedelta(hours=24)
        end = pd.Timestamp.utcnow()

        data = {}
        total = 0.0
        latest_timestamp = None

        for zone in ZONES:
            try:
                # Returns a Pandas Series or DataFrame depending on resolution/types
                ts = client.query_generation(zone, start=start, end=end)

                # Check if we have Solar column
                if "Solar" in ts.columns:
                    val = ts["Solar"].iloc[-1]
                    idx = ts.index[-1]
                    if isinstance(val, pd.Series):
                        val = val.iloc[0]
                    val = float(val)

                    # If it's night time, the value could be 0, which is perfectly valid.
                    if pd.isna(val):
                        val = 0.0

                    data[zone] = val
                    total += val
                    
                    if idx is not None:
                        ts_formatted = idx.isoformat()
                        if latest_timestamp is None or ts_formatted > latest_timestamp:
                            latest_timestamp = ts_formatted
                else:
                    data[zone] = None
            except Exception as e:
                logger.error(f"Error fetching {zone} from ENTSO-E: {e}")
                data[zone] = None

        data["totalGen"] = total
        if latest_timestamp:
            data["timestamp"] = latest_timestamp

        if total == 0 and all(v == 0 for v in data.values()):
            logger.warning(
                "No solar generation data found in ENTSO-E response for any Italy zone."
            )
            # At night it's 0, so returning it is technically fine, but if it's
            # genuinely missing, we just return the 0s.

        return data

    except Exception as e:
        logger.error(f"ENTSO-E live fetch failed for Italy: {e}")
        return None
