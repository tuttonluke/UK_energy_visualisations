from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from services.elexon import fetch_bmrs_generation


@pytest.mark.asyncio
@patch("services.elexon.get_client")
async def test_fetch_bmrs_generation_success(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"startTime": "2026-07-08T12:00:00Z", "data": []},
        {"startTime": "2026-07-08T12:30:00Z", "data": []},
    ]
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    data, min_dt, max_dt = await fetch_bmrs_generation()

    assert data is not None
    assert len(data) == 2
    assert min_dt.isoformat() == "2026-07-08T12:00:00+00:00"
    assert max_dt.isoformat() == "2026-07-08T12:30:00+00:00"


@pytest.mark.asyncio
@patch("services.elexon.get_client")
async def test_fetch_bmrs_generation_empty(mock_get_client):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    data, min_dt, max_dt = await fetch_bmrs_generation()

    assert data is None
    assert min_dt is None
    assert max_dt is None


@pytest.mark.asyncio
@patch("services.elexon.get_client")
async def test_fetch_bmrs_generation_error(mock_get_client):
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=Exception("API down"))
    mock_get_client.return_value = mock_client

    data, min_dt, max_dt = await fetch_bmrs_generation()

    assert data is None
    assert min_dt is None
    assert max_dt is None
