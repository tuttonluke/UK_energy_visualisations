from unittest.mock import AsyncMock, MagicMock, patch


def test_proxy_mapbox_endpoint_missing_path(client):
    response = client.get("/api/proxy/mapbox")
    assert response.status_code == 422  # Missing required 'path' parameter


@patch("main.MAPBOX_ACCESS_TOKEN", None)
def test_proxy_mapbox_endpoint_missing_token(client):
    response = client.get(
        "/api/proxy/mapbox?path=/v4/mapbox.mapbox-streets-v8/1/0/0.mvt"
    )
    assert response.status_code == 500
    assert response.json() == {"detail": "Mapbox token not configured"}


@patch("main.MAPBOX_ACCESS_TOKEN", "fake_token")
@patch("main.quota_service.check_and_increment_quota", return_value=False)
def test_proxy_mapbox_endpoint_quota_exceeded(mock_quota, client):
    response = client.get(
        "/api/proxy/mapbox?path=/v4/mapbox.mapbox-streets-v8/1/0/0.mvt"
    )
    assert response.status_code == 429
    assert response.json() == {"detail": "Mapbox monthly quota exceeded"}


@patch("main.MAPBOX_ACCESS_TOKEN", "fake_token")
@patch("main.quota_service.check_and_increment_quota", return_value=True)
@patch("httpx.AsyncClient.send")
def test_proxy_mapbox_endpoint_success(mock_send, mock_quota, client):

    # Mock httpx response stream
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/x-protobuf"}

    async def mock_aiter_raw():
        yield b"mock_data"

    mock_response.aiter_raw = mock_aiter_raw
    mock_response.aclose = AsyncMock()
    mock_send.return_value = mock_response

    response = client.get(
        "/api/proxy/mapbox?path=/v4/mapbox.mapbox-streets-v8/1/0/0.mvt"
    )

    assert response.status_code == 200
    assert response.content == b"mock_data"
    assert response.headers["content-type"] == "application/x-protobuf"


def test_river_levels_endpoint_empty_cache(empty_client):
    response = empty_client.get("/api/environment/river_levels")
    assert response.status_code == 503
    assert response.json() == {
        "detail": "River level data is currently unavailable. Please try again later."
    }


def test_river_levels_endpoint(client):
    # Pre-populate stations cache to avoid timeout and test valid filtering
    client.app.state.river_stations_store._data = {
        "123": {
            "stationReference": "123",
            "label": "Test Station",
            "riverName": "Test River",
            "lat": 51.5,
            "long": -0.1,
            "typicalRangeLow": 0.5,
            "typicalRangeHigh": 1.5,
        }
    }
    client.app.state.river_readings_store._data = [{"measure": "123", "value": 0.5}]
    client.app.state.river_stations_store._initialized = True
    client.app.state.river_readings_store._initialized = True

    response = client.get("/api/environment/river_levels")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 1
    assert data["data"][0]["stationReference"] == "123"
    assert data["data"][0]["value"] == 0.5


def test_generation_endpoint_empty_cache(empty_client):
    response = empty_client.get("/api/generation/summary")
    assert response.status_code == 503
    assert response.json() == {
        "detail": "Generation data is currently unavailable. Please try again later."
    }


def test_solar_endpoint_empty_cache(empty_client):
    response = empty_client.get("/api/solar/solar")
    assert response.status_code == 503
    assert response.json() == {
        "detail": "Solar data is currently unavailable. Please try again later."
    }


def test_solar_endpoint(client):
    response = client.get("/api/solar/solar")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


def test_generation_endpoint(client):
    response = client.get("/api/generation/summary")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
