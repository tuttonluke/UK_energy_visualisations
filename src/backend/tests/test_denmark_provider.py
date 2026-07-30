from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from services.energy_providers.denmark import DenmarkProvider


@pytest.mark.asyncio
@patch("services.energy_providers.denmark.get_client")
async def test_denmark_provider_success(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    # Denmark API returns something like:
    # {"records": [{"Minutes5UTC": "2026-07-30T12:00:00", "SolarPower": 30.5}]}
    mock_response.json.return_value = {
        "records": [
            {
                "Minutes5UTC": "2026-07-30T12:00:00",
                "SolarPower": 30.5,
                "PriceArea": "DK1",
            },
            {
                "Minutes5UTC": "2026-07-30T12:05:00",
                "SolarPower": 32.0,
                "PriceArea": "DK2",
            },
        ]
    }
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    provider = DenmarkProvider("solar")
    data = await provider._do_fetch()

    assert data is not None
    assert "totalGen" in data
    assert data["totalGen"] == {"solar": 62.5}
    assert data["DK1"] == {"solar": 30.5}
    assert data["DK2"] == {"solar": 32.0}
    assert data["timestamp"] == "2026-07-30T12:05:00Z"


@pytest.mark.asyncio
@patch("services.energy_providers.denmark.get_client")
async def test_denmark_provider_empty_records(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"records": []}
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    provider = DenmarkProvider("solar")
    data = await provider._do_fetch()

    assert data is None


@pytest.mark.asyncio
@patch("services.energy_providers.denmark.get_client")
async def test_denmark_provider_missing_field(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    # Missing SolarPower field
    mock_response.json.return_value = {
        "records": [{"Minutes5UTC": "2026-07-30T12:00:00"}]
    }
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    provider = DenmarkProvider("solar")
    data = await provider._do_fetch()

    assert data is None


@pytest.mark.asyncio
@patch("services.energy_providers.denmark.get_client")
async def test_denmark_provider_error(mock_get_client):
    import httpx

    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=httpx.HTTPError("API Error"))
    mock_get_client.return_value = mock_client

    provider = DenmarkProvider("solar")
    with pytest.raises(httpx.HTTPError):
        await provider._do_fetch()
