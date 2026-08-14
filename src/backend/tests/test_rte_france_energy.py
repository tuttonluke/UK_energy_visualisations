"""
===============================================================================
File: test_rte_france_energy.py
Description: Tests for the RTE France energy provider.
Date: 2026-08-14
License: MIT License
===============================================================================
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from services.energy_providers.rte_france_energy import RteProvider


@pytest.mark.asyncio
@patch("services.energy_providers.rte_france_energy.get_client")
async def test_rte_provider_success(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "code_insee_region": "11",
                "solaire": 10.5,
                "date_heure": "2026-07-30T12:00:00+00:00",
            },
            {
                "code_insee_region": "24",
                "solaire": 20.0,
                "date_heure": "2026-07-30T12:00:00+00:00",
            },
            # Duplicate region to test taking the first (latest) value
            {
                "code_insee_region": "11",
                "solaire": 5.0,
                "date_heure": "2026-07-30T11:30:00+00:00",
            },
        ]
    }
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    provider = RteProvider("solar")
    data = await provider._do_fetch()

    assert data is not None
    assert "totalGen" in data
    assert data["totalGen"] == {"solar": 30.5}
    assert data["11"] == {"solar": 10.5}
    assert data["24"] == {"solar": 20.0}
    assert data["timestamp"] == "2026-07-30T12:00:00Z"


@pytest.mark.asyncio
@patch("services.energy_providers.rte_france_energy.get_client")
async def test_rte_provider_empty_results(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    provider = RteProvider("solar")
    data = await provider._do_fetch()

    assert data is not None
    assert data["totalGen"] == {"solar": 0.0}


@pytest.mark.asyncio
@patch("services.energy_providers.rte_france_energy.get_client")
async def test_rte_provider_error(mock_get_client):
    import httpx

    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=httpx.HTTPError("API Error"))
    mock_get_client.return_value = mock_client

    provider = RteProvider("solar")
    with pytest.raises(httpx.HTTPError):
        await provider._do_fetch()
