"""
===============================================================================
File: test_elia_belgium_energy.py
Description: Tests for the Elia Belgium energy provider.
Date: 2026-08-14
License: MIT License
===============================================================================
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from services.energy_providers.elia_belgium_energy import EliaProvider


@pytest.mark.asyncio
@patch("services.energy_providers.elia_belgium_energy.get_client")
async def test_elia_provider_success(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "region": "Flanders",
                "realtime": 100.5,
                "datetime": "2026-07-30T12:00:00+00:00",
            },
            {
                "region": "Wallonia",
                "realtime": None,
                "mostrecentforecast": 50.0,
                "datetime": "2026-07-30T12:00:00+00:00",
            },
            {
                "region": "Brussels",
                "realtime": 10.0,
                "datetime": "2026-07-30T12:00:00+00:00",
            },
        ]
    }
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    provider = EliaProvider("solar")
    data = await provider._do_fetch()

    assert data is not None
    assert "totalGen" in data
    assert data["totalGen"] == {"solar": 160.5}
    assert data["Flanders"] == {"solar": 100.5}
    assert data["Région wallonne"] == {"solar": 50.0}
    assert data["Brussels"] == {"solar": 10.0}
    assert data["timestamp"] == "2026-07-30T12:00:00Z"


@pytest.mark.asyncio
@patch("services.energy_providers.elia_belgium_energy.get_client")
async def test_elia_provider_empty_results(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    provider = EliaProvider("solar")
    data = await provider._do_fetch()

    assert data is not None
    assert data["totalGen"] == {"solar": 0.0}


@pytest.mark.asyncio
@patch("services.energy_providers.elia_belgium_energy.get_client")
async def test_elia_provider_error(mock_get_client):
    import httpx

    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=httpx.HTTPError("API down"))
    mock_get_client.return_value = mock_client

    provider = EliaProvider("solar")
    with pytest.raises(httpx.HTTPError):
        await provider._do_fetch()
