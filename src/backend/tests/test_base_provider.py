from unittest.mock import AsyncMock, patch

import pytest
from services.energy_providers.base import BaseEnergyProvider, format_nested_data


class DummyProvider(BaseEnergyProvider):
    async def _do_fetch(self):
        return {"totalGen": {"solar": 100}, "timestamp": "2026-07-30T12:00:00Z"}


@pytest.mark.asyncio
async def test_format_nested_data():
    flat = {"totalGen": 100, "region_A": 50, "timestamp": "time"}
    nested = format_nested_data(flat, "wind")

    assert nested["totalGen"] == {"wind": 100}
    assert nested["region_A"] == {"wind": 50}
    assert nested["timestamp"] == "time"


@pytest.mark.asyncio
async def test_base_provider_success():
    provider = DummyProvider("uk", "solar")
    data = await provider.fetch_live_data()
    assert data["totalGen"] == {"solar": 100}


@pytest.mark.asyncio
@patch("services.energy_providers.base.asyncio.sleep", new_callable=AsyncMock)
async def test_base_provider_retry(mock_sleep):
    provider = DummyProvider("uk", "solar")

    # Make _do_fetch fail twice, then succeed
    provider._do_fetch = AsyncMock(
        side_effect=[Exception("fail"), Exception("fail"), {"totalGen": {"solar": 50}}]
    )

    data = await provider.fetch_live_data()
    assert data["totalGen"] == {"solar": 50}
    assert provider._do_fetch.call_count == 3
    assert mock_sleep.call_count == 2


@pytest.mark.asyncio
@patch("services.energy_providers.base.asyncio.sleep", new_callable=AsyncMock)
async def test_base_provider_fallback(mock_sleep):
    provider = DummyProvider("uk", "solar")

    # Store previous data manually
    provider._previous_data = {"totalGen": {"solar": 42}, "timestamp": "old_time"}

    # Make _do_fetch fail continuously
    provider._do_fetch = AsyncMock(side_effect=Exception("fail"))

    data = await provider.fetch_live_data()
    assert data["totalGen"] == {"solar": 42}
    assert data["timestamp"] == "old_time"
    assert provider._do_fetch.call_count == 3
    assert mock_sleep.call_count == 2
