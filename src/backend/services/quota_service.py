import asyncio
import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

QUOTA_FILE = os.path.join(os.path.dirname(__file__), "..", "mapbox_quota.json")
MONTHLY_LIMIT = 150000

# In-memory quota state — avoids blocking file I/O on every request
_quota_lock = asyncio.Lock()
_quota_month = ""
_quota_count = 0
_initialized = False


def _get_current_month():
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _load_from_disk():
    """Load saved quota data from disk on first access."""
    current_month = _get_current_month()
    if os.path.exists(QUOTA_FILE):
        try:
            with open(QUOTA_FILE, "r") as f:
                saved_data = json.load(f)
                if saved_data.get("month") == current_month:
                    return current_month, saved_data.get("count", 0)
        except Exception as e:
            logger.error(f"Failed to read mapbox quota file: {e}")
    return current_month, 0


def _save_to_disk(month, count):
    """Persist quota state to disk (called infrequently)."""
    try:
        with open(QUOTA_FILE, "w") as f:
            json.dump({"month": month, "count": count}, f)
    except Exception as e:
        logger.error(f"Failed to write mapbox quota file: {e}")


async def check_and_increment_quota() -> bool:
    """
    Checks if the monthly Mapbox quota has been exceeded.
    If not, increments the counter and returns True.
    If exceeded, returns False.

    Uses in-memory counter with asyncio.Lock to avoid blocking
    file I/O on every concurrent tile request.
    """
    global _quota_month, _quota_count, _initialized

    async with _quota_lock:
        current_month = _get_current_month()

        # First access or month rollover — load/reset
        if not _initialized or current_month != _quota_month:
            _quota_month, _quota_count = _load_from_disk()
            # Handle month rollover
            if current_month != _quota_month:
                _quota_month = current_month
                _quota_count = 0
            _initialized = True

        # Check if we've hit the limit
        if _quota_count >= MONTHLY_LIMIT:
            logger.warning(f"Mapbox monthly limit of {MONTHLY_LIMIT} reached!")
            return False

        # Increment
        _quota_count += 1

        # Save every 100 requests to avoid excessive disk I/O,
        # but ensure the very first request of the month is saved.
        # Use asyncio.to_thread to avoid blocking the event loop.
        if _quota_count % 100 == 0 or _quota_count == 1:
            count, month = _quota_count, _quota_month
            await asyncio.to_thread(_save_to_disk, month, count)

        return True
