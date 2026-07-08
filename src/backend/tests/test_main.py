from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_get_config():
    """Test that the config endpoint returns a 200 OK and a JSON object."""

    response = client.get("/api/config")
    assert response.status_code == 200
    assert "mapboxToken" in response.json()
