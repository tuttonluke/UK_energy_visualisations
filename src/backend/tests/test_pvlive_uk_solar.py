from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from services.energy_providers.pvlive_uk_solar import PVLiveProvider


@pytest.mark.asyncio
@patch("services.energy_providers.pvlive_uk_solar.get_client")
async def test_fetch_pvlive_history_success(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    # data format: [pes_id, datetime, generation]
    mock_response.json.return_value = {
        "data": [[0, "2026-07-08T12:00:00Z", 100], [0, "2026-07-08T12:30:00Z", 150]]
    }
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    provider = PVLiveProvider("solar")
    result = await provider._do_fetch_history()

    assert result is not None
    assert "2026-07-08T12:00:00Z" in result
    assert result["2026-07-08T12:00:00Z"] == 100
    assert result["2026-07-08T12:30:00Z"] == 150


@pytest.mark.asyncio
@patch("services.energy_providers.pvlive_uk_solar.get_client")
async def test_fetch_pvlive_history_error(mock_get_client):
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=Exception("API Error"))
    mock_get_client.return_value = mock_client

    provider = PVLiveProvider("solar")
    result = await provider._do_fetch_history()
    assert result is None


@pytest.mark.asyncio
async def test_fetch_pes_region_data_success():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [[10, "time", 42.5]]}

    # We must patch an async get directly or mock it properly
    async def mock_get(*args, **kwargs):
        return mock_response

    mock_client.get = mock_get

    provider = PVLiveProvider("solar")
    pes_id, gen, time = await provider.fetch_pes_region_data(mock_client, 10)
    assert pes_id == "10"
    assert gen == 42.5
    assert time == "time"


@pytest.mark.asyncio
@patch.object(PVLiveProvider, "fetch_pes_region_data")
@patch("services.energy_providers.pvlive_uk_solar.get_client")
async def test_fetch_pvlive_live_success(mock_get_client, mock_fetch_pes):
    # Mock PES responses
    # Returns (pes_id_str, generation, time_str)
    mock_fetch_pes.side_effect = [(str(i), i * 10, "time") for i in range(10, 24)]

    provider = PVLiveProvider("solar")
    result = await provider.fetch_live_data()

    assert "10" in result
    assert result["10"] == {"solar": 100.0}
    assert "23" in result
    assert result["23"] == {"solar": 230.0}
    assert result["totalGen"] == {"solar": 2310.0}
    assert result["timestamp"] == "time"
