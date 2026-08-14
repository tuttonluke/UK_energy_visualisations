"""
===============================================================================
File: test_entsoe_energy.py
Description: Tests for the ENTSO-E energy provider.
Date: 2026-08-14
License: MIT License
===============================================================================
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from services.energy_providers.entsoe_energy import EntsoeProvider


@pytest.mark.asyncio
@patch.dict("os.environ", {"ENTSOE_TOKEN": "test_token"})
@patch("services.energy_providers.entsoe_energy.EntsoePandasClient")
async def test_entsoe_provider_success(mock_client_class):
    mock_client = MagicMock()

    # Create a dummy DataFrame with time index
    idx = pd.date_range("2026-07-30 12:00:00", periods=2, freq="h", tz="UTC")
    df = pd.DataFrame({"Solar": [10.5, 12.0]}, index=idx)
    mock_client.query_generation.return_value = df
    mock_client_class.return_value = mock_client

    provider = EntsoeProvider("se", "solar", {"SE1": "SE_1"})
    data = await provider._do_fetch()

    assert data is not None
    assert "totalGen" in data
    assert data["totalGen"] == {"solar": 12.0}
    assert data["SE1"] == {"solar": 12.0}
    assert data["timestamp"] == "2026-07-30T13:00:00+00:00"


@pytest.mark.asyncio
@patch.dict("os.environ", {"ENTSOE_TOKEN": "test_token"})
@patch("services.energy_providers.entsoe_energy.EntsoePandasClient")
async def test_entsoe_provider_empty_df(mock_client_class):
    mock_client = MagicMock()
    mock_client.query_generation.return_value = pd.DataFrame()
    mock_client_class.return_value = mock_client

    provider = EntsoeProvider("ie", "solar", ["IE"])
    data = await provider._do_fetch()

    assert data is not None
    assert data["totalGen"] == {"solar": 0.0}
    assert data["IE"] == {"solar": 0.0}


@pytest.mark.asyncio
@patch.dict("os.environ", {"ENTSOE_TOKEN": "test_token"})
@patch("services.energy_providers.entsoe_energy.EntsoePandasClient")
async def test_entsoe_provider_error(mock_client_class):
    mock_client = MagicMock()
    mock_client.query_generation.side_effect = Exception("API down")
    mock_client_class.return_value = mock_client

    provider = EntsoeProvider("ie", "solar", ["IE"])
    data = await provider._do_fetch()

    assert data is not None
    assert data["totalGen"] == {"solar": 0.0}
    assert data["IE"] == {"solar": 0.0}


def test_entsoe_provider_no_token():
    with patch.dict("os.environ", clear=True):
        provider = EntsoeProvider("ie", "solar", ["IE"])
        with pytest.raises(ValueError, match="ENTSOE_TOKEN not found"):
            provider._get_client()
