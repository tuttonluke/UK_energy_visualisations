from unittest.mock import MagicMock, patch

import pytest
from main import app


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_solar_data_fetching(mock_get, empty_client):
    """Test that the solar cache aggregates data correctly from the API."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [["2024-01-01T12:00:00Z", 10, 150.5]]}
    mock_get.return_value = mock_response

    await app.state.solar_uk_store.update()

    response = empty_client.get("/api/solar/solar")
    data = response.json()

    assert response.status_code == 200
    assert "10" in data
    assert data["10"] == 150.5

    expected_total = round(150.5 * 14, 1)
    assert data["totalGen"] == expected_total
    assert mock_get.call_count == 14


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_solar_cache_logic(mock_get, empty_client):
    """Test that subsequent calls to the endpoint do not hit the external API."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [["date", 10, 100.0]]}
    mock_get.return_value = mock_response

    # Force a cache update
    await app.state.solar_uk_store.update()
    assert mock_get.call_count == 14

    mock_get.reset_mock()

    # The endpoint simply returns the cache, no external calls
    empty_client.get("/api/solar/solar")
    assert mock_get.call_count == 0


def test_solar_france_endpoint_empty_cache(empty_client):
    response = empty_client.get("/api/solar/solar/france")
    assert response.status_code == 503
    assert response.json() == {
        "detail": "French solar data is currently unavailable. Please try again later."
    }


def test_solar_france_endpoint(client):
    response = client.get("/api/solar/solar/france")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data["totalGen"] == 50
    assert data["75"] == 50
