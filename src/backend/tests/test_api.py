import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_config_endpoint():
    response = client.get("/api/config")
    assert response.status_code == 200
    assert "mapboxToken" in response.json()

def test_regions_endpoint():
    response = client.get("/api/regions")
    assert response.status_code == 200
    assert "type" in response.json() or "error" in response.json()

def test_solar_endpoint():
    response = client.get("/api/solar/solar")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    
def test_generation_endpoint():
    response = client.get("/api/generation/summary")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
