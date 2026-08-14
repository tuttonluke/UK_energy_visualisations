"""
===============================================================================
File: test_uk_environment_agency.py
Description: Tests for the UK Environment Agency provider.
Date: 2026-08-14
License: MIT License
===============================================================================
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from services.environment_providers.uk_environment_agency import (
    EnvironmentAgencyProvider,
)


@pytest.mark.asyncio
@patch("services.environment_providers.uk_environment_agency.get_client")
async def test_fetch_ea_stations_success(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "items": [
            {
                "stationReference": "123",
                "label": ["Station 1"],
                "riverName": "River Thames",
                "lat": [51.5],
                "long": [-0.1],
                "stageScale": {"typicalRangeLow": 0.5, "typicalRangeHigh": 2.5},
                "measures": [{"@id": "http://measure/123"}],
            }
        ]
    }
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    provider = EnvironmentAgencyProvider()
    result = await provider._do_fetch_stations()

    assert result is not None
    assert "http://measure/123" in result
    station = result["http://measure/123"]
    assert station["label"] == "Station 1"
    assert station["lat"] == 51.5
    assert station["typicalRangeHigh"] == 2.5


@pytest.mark.asyncio
@patch("services.environment_providers.uk_environment_agency.get_client")
async def test_fetch_ea_stations_error(mock_get_client):
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=Exception("EA API down"))
    mock_get_client.return_value = mock_client

    provider = EnvironmentAgencyProvider()
    with pytest.raises(Exception, match="EA API down"):
        await provider._do_fetch_stations()


@pytest.mark.asyncio
@patch("services.environment_providers.uk_environment_agency.get_client")
async def test_fetch_ea_readings_success(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "items": [{"measure": "http://measure/123", "value": 1.2}]
    }
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    provider = EnvironmentAgencyProvider()
    result = await provider._do_fetch_readings()

    assert result is not None
    assert len(result) == 1
    assert result[0]["value"] == 1.2


@pytest.mark.asyncio
@patch("services.environment_providers.uk_environment_agency.get_client")
async def test_fetch_ea_readings_error(mock_get_client):
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=Exception("EA API down"))
    mock_get_client.return_value = mock_client

    provider = EnvironmentAgencyProvider()
    with pytest.raises(Exception, match="EA API down"):
        await provider._do_fetch_readings()
