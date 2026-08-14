"""
===============================================================================
File: test_fraunhofer_energy_charts.py
Description: Tests for the Fraunhofer Energy Charts provider.
Date: 2026-08-14
License: MIT License
===============================================================================
"""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from services.energy_providers.fraunhofer_energy_charts import EnergyChartsProvider


@pytest.mark.asyncio
@patch(
    "services.energy_providers.fraunhofer_energy_charts.asyncio.sleep",
    new_callable=AsyncMock,
)
@patch("services.energy_providers.fraunhofer_energy_charts.get_client")
async def test_energy_charts_provider_success(mock_get_client, mock_sleep):
    mock_client = MagicMock()
    mock_response = MagicMock()
    # Mocking unix seconds and production types
    unix_seconds = [1700000000, 1700003600]
    mock_response.json.return_value = {
        "unix_seconds": unix_seconds,
        "production_types": [
            {"name": "Wind onshore", "data": [10.0, 12.0]},
            {"name": "Solar", "data": [50.0, 55.5]},
        ],
    }
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    provider = EnergyChartsProvider("de", "solar")
    data = await provider._do_fetch()

    assert data is not None
    assert "totalGen" in data
    assert data["totalGen"] == {"solar": 55.5}
    expected_time = datetime.datetime.fromtimestamp(
        unix_seconds[1], tz=datetime.timezone.utc
    ).isoformat()
    assert data["timestamp"] == expected_time
    assert mock_sleep.call_count == 1


@pytest.mark.asyncio
@patch(
    "services.energy_providers.fraunhofer_energy_charts.asyncio.sleep",
    new_callable=AsyncMock,
)
@patch("services.energy_providers.fraunhofer_energy_charts.get_client")
async def test_energy_charts_provider_missing_source(mock_get_client, mock_sleep):
    mock_client = MagicMock()
    mock_response = MagicMock()
    # Missing Solar production type
    mock_response.json.return_value = {
        "unix_seconds": [1700000000],
        "production_types": [{"name": "Wind onshore", "data": [10.0]}],
    }
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    provider = EnergyChartsProvider("de", "solar")
    data = await provider._do_fetch()

    assert data is None


@pytest.mark.asyncio
@patch(
    "services.energy_providers.fraunhofer_energy_charts.asyncio.sleep",
    new_callable=AsyncMock,
)
@patch("services.energy_providers.fraunhofer_energy_charts.get_client")
async def test_energy_charts_provider_error(mock_get_client, mock_sleep):
    import httpx

    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=httpx.HTTPError("API limit"))
    mock_get_client.return_value = mock_client

    provider = EnergyChartsProvider("de", "solar")
    with pytest.raises(httpx.HTTPError):
        await provider._do_fetch()
