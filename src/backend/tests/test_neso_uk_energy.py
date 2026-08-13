from datetime import datetime, timezone

import pytest
from services.energy_providers.neso_uk_energy import parse_neso_datetime


def test_parse_neso_datetime_standard():
    dt = parse_neso_datetime("2026-07-08T00:00:00", "12:30")
    assert dt == datetime(2026, 7, 8, 12, 30, tzinfo=timezone.utc)

    dt = parse_neso_datetime("2026-07-08", "12:30")
    assert dt == datetime(2026, 7, 8, 12, 30, tzinfo=timezone.utc)


def test_parse_neso_datetime_short_time():
    dt = parse_neso_datetime("2026-07-08", "9:30")
    assert dt == datetime(2026, 7, 8, 9, 30, tzinfo=timezone.utc)


def test_parse_neso_datetime_24_00_rollover():
    dt = parse_neso_datetime("2026-07-08", "24:00")
    assert dt == datetime(2026, 7, 9, 0, 0, tzinfo=timezone.utc)

    dt = parse_neso_datetime("2026-02-28", "24:00")
    assert dt == datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)


def test_parse_neso_datetime_with_seconds():
    dt = parse_neso_datetime("2026-07-08", "12:30:45")
    assert dt == datetime(2026, 7, 8, 12, 30, 45, tzinfo=timezone.utc)


def test_parse_neso_datetime_invalid():
    with pytest.raises(ValueError):
        parse_neso_datetime("", "12:30")

    with pytest.raises(ValueError):
        parse_neso_datetime("2026-07-08", "")

    with pytest.raises(ValueError, match="Could not parse NESO datetime"):
        parse_neso_datetime("2026-07-08", "invalid")
