"""
===============================================================================
File: test_api.py
Description: Tests for the FastAPI router endpoints.
Date: 2026-08-14
License: MIT License
===============================================================================
"""


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


def test_generation_endpoint(client):
    response = client.get("/api/generation/summary")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
