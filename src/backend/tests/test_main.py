import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import main
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    """
    Because SOLAR_CACHE is a global variable, state will leak between tests.
    This fixture runs before every test (autouse=True) to wipe the cache clean.
    The 'yield' keyword separates the SetUp phase from the TearDown phase.
    """
    main.SOLAR_CACHE = {}
    main.LAST_FETCH_TIME = 0

    yield


def test_get_config():
    """Test that the config endpoint returns a 200 OK and a JSON object."""

    response = client.get("/api/config")
    assert response.status_code == 200
    assert "mapboxToken" in response.json()


@patch("main.httpx.AsyncClient.get")
def test_solar_data_fetching(mock_get):
    """Test that the solar endpoint aggregates data correctly from the API."""

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [["2024-01-01T12:00:00Z", 10, 150.5]]}

    mock_get.return_value = mock_response

    response = client.get("/api/solar")
    data = response.json()

    assert response.status_code == 200
    assert "10" in data
    assert data["10"] == 150.5

    expected_total = round(150.5 * 14, 1)
    assert data["total_gen"] == expected_total
    assert mock_get.call_count == 14


@patch("main.httpx.AsyncClient.get")
def test_solar_cache_logic(mock_get):
    """Test that subsequent calls within 5 minutes do not hit the external API."""

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [["date", 10, 100.0]]}
    mock_get.return_value = mock_response

    client.get("/api/solar")
    assert mock_get.call_count == 14

    mock_get.reset_mock()

    client.get("api/solar")
    assert mock_get.call_count == 0
