"""
===============================================================================
File: test_solar_router.py
Description: Tests for the solar API router.
Date: 2026-08-14
License: MIT License
===============================================================================
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_solar_data_fetching(mock_get, empty_client):
    """Test that the solar cache aggregates data correctly from the API."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [["some_zone", "2024-01-01T12:00:00Z", 150.5]]
    }
    mock_get.return_value = mock_response

    from services.energy_providers.pvlive_uk_solar import PVLiveProvider

    provider = PVLiveProvider("solar")
    data = await provider.fetch_live_data()

    assert "10" in data or "totalGen" in data
    assert data["totalGen"] == {"solar": round(150.5 * 14, 1)}
    assert mock_get.call_count == 14


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_solar_cache_logic(mock_get, empty_client):
    """Test that subsequent calls to the endpoint do not hit the external API."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [["some_zone", "2024-01-01T12:00:00Z", 100.0]]
    }
    mock_get.return_value = mock_response

    from services.energy_providers.pvlive_uk_solar import PVLiveProvider

    provider = PVLiveProvider("solar")
    await provider.fetch_live_data()
    assert mock_get.call_count == 14

    mock_get.reset_mock()
    # Mocking cache_store means hitting the endpoint won't call the API
    empty_client.get("/api/solar/uk")
    assert mock_get.call_count == 0


def test_solar_france_endpoint_empty_cache(empty_client):
    response = empty_client.get("/api/solar/france")
    assert response.status_code == 503
    assert response.json() == {
        "detail": "Solar data for france is currently unavailable. Please try again later."
    }


def test_solar_france_endpoint(client):
    response = client.get("/api/solar/france")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data["totalGen"] == {"solar": 50}
    assert data["75"] == {"solar": 50}


def test_energy_charts_endpoint_empty_cache(empty_client):
    response = empty_client.get("/api/solar/energy_charts")
    assert response.status_code == 503
    assert response.json() == {
        "detail": "Solar data for energy_charts is currently unavailable. Please try again later."
    }


def test_energy_charts_endpoint(client):
    response = client.get("/api/solar/energy_charts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data["de"]["totalGen"] == {"solar": 120}
    assert data["nl"]["totalGen"] == {"solar": 80}


def test_solar_denmark_endpoint_empty_cache(empty_client):
    response = empty_client.get("/api/solar/denmark")
    assert response.status_code == 503
    assert response.json() == {
        "detail": "Solar data for denmark is currently unavailable. Please try again later."
    }


def test_solar_denmark_endpoint(client):
    response = client.get("/api/solar/denmark")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data["totalGen"] == {"solar": 30}


def test_solar_belgium_endpoint_empty_cache(empty_client):
    response = empty_client.get("/api/solar/belgium")
    assert response.status_code == 503
    assert response.json() == {
        "detail": "Solar data for belgium is currently unavailable. Please try again later."
    }


def test_solar_belgium_endpoint(client):
    response = client.get("/api/solar/belgium")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data["totalGen"] == {"solar": 40}
