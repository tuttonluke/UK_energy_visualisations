from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from services.energy_providers.elexon_uk_bmrs import BMRSProvider


@pytest.mark.asyncio
@patch("services.energy_providers.elexon_uk_bmrs.get_client")
async def test_fetch_bmrs_generation_success(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"startTime": "2026-07-08T12:00:00Z", "data": []},
        {"startTime": "2026-07-08T12:30:00Z", "data": []},
    ]
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    provider = BMRSProvider()
    result = await provider._do_fetch()

    assert result is not None
    data = result["data"]
    assert len(data) == 2
    assert result["min_dt"].isoformat() == "2026-07-08T12:00:00+00:00"
    assert result["max_dt"].isoformat() == "2026-07-08T12:30:00+00:00"


@pytest.mark.asyncio
@patch("services.energy_providers.elexon_uk_bmrs.get_client")
async def test_fetch_bmrs_generation_empty(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    provider = BMRSProvider()
    result = await provider._do_fetch()

    assert result is None


@pytest.mark.asyncio
@patch("services.energy_providers.elexon_uk_bmrs.get_client")
async def test_fetch_bmrs_generation_error(mock_get_client):
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=Exception("API down"))
    mock_get_client.return_value = mock_client

    provider = BMRSProvider()
    with pytest.raises(Exception):
        await provider._do_fetch()
