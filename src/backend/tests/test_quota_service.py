from unittest.mock import mock_open, patch

import pytest
import services.quota_service as quota_service
from services.quota_service import check_and_increment_quota


@pytest.fixture(autouse=True)
def reset_quota_state():
    """Reset the global state of quota_service before and after each test."""
    quota_service._initialized = False
    quota_service._quota_count = 0
    quota_service._quota_month = ""
    yield
    quota_service._initialized = False
    quota_service._quota_count = 0
    quota_service._quota_month = ""


@pytest.mark.asyncio
@patch("services.quota_service._get_current_month", return_value="2026-07")
@patch("os.path.exists", return_value=True)
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='{"month": "2026-07", "count": 10}',
)
async def test_quota_within_limit(mock_file, mock_exists, mock_month):
    """Test standard increment when within limit."""
    with patch("asyncio.to_thread") as mock_to_thread:
        # 1st request (loads from disk, increments from 10 to 11)
        # doesn't save because it's not % 100 or == 1 (it's 11)
        allowed = await check_and_increment_quota()
        assert allowed is True
        assert quota_service._quota_count == 11
        mock_to_thread.assert_not_called()


@pytest.mark.asyncio
@patch("services.quota_service._get_current_month", return_value="2026-07")
@patch("os.path.exists", return_value=True)
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='{"month": "2026-07", "count": 150000}',
)
async def test_quota_at_limit(mock_file, mock_exists, mock_month):
    """Test rejection when at limit."""
    with patch("asyncio.to_thread"):
        allowed = await check_and_increment_quota()
        assert allowed is False
        assert quota_service._quota_count == 150000


@pytest.mark.asyncio
@patch("services.quota_service._get_current_month", return_value="2026-08")
@patch("os.path.exists", return_value=True)
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='{"month": "2026-07", "count": 149999}',
)
async def test_quota_month_rollover(mock_file, mock_exists, mock_month):
    """Test that a new month resets the counter to 0 before incrementing."""
    with patch("asyncio.to_thread") as mock_to_thread:
        allowed = await check_and_increment_quota()
        assert allowed is True
        # Starts at 0, increments to 1
        assert quota_service._quota_count == 1
        assert quota_service._quota_month == "2026-08"
        # Since it's count == 1, it should save
        mock_to_thread.assert_called_once()


@pytest.mark.asyncio
@patch("services.quota_service._get_current_month", return_value="2026-07")
@patch("os.path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data="{corrupt_json: true")
async def test_quota_corrupt_file(mock_file, mock_exists, mock_month):
    """Test fallback to 0 if the quota file is corrupt."""
    with patch("asyncio.to_thread"):
        allowed = await check_and_increment_quota()
        assert allowed is True
        # Falls back to 0, increments to 1
        assert quota_service._quota_count == 1
