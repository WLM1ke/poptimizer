from datetime import date

import pytest

from poptimizer import errors
from poptimizer.domain import domain
from poptimizer.domain.moex import usd


def test_row_parse():
    row = usd.Row(
        day=date(2025, 1, 27),
        open=1,
        close=2,
        high=3,
        low=1,
        turnover=10,
    )
    parsed = usd.Row.model_validate(
        {
            "begin": "2025-01-27",
            "open": 1,
            "close": 2,
            "high": 3,
            "low": 1,
            "value": 10,
        }
    )
    assert row == parsed


def test_row_invalid():
    with pytest.raises(ValueError, match="Input should be greater than 0"):
        usd.Row.model_validate(
            {
                "begin": "2025-01-27",
                "open": -1,
                "close": 2,
                "high": 3,
                "low": 1,
                "value": 10,
            }
        )


def test_usd_not_sorted_df():
    with pytest.raises(ValueError, match="df not sorted by day"):
        usd.USD(
            day=date(2025, 1, 27),
            rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(42)),
            df=[
                usd.Row(day=date(2025, 1, 28), open=1, close=2, high=3, low=1, turnover=10),
                usd.Row(day=date(2025, 1, 27), open=1, close=2, high=3, low=1, turnover=10),
            ],
        )


def test_usd_update_no_df():
    update_day = date(2025, 1, 29)
    rows = [
        usd.Row(day=date(2025, 1, 27), open=1, close=2, high=3, low=1, turnover=10),
        usd.Row(day=date(2025, 1, 28), open=2, close=3, high=4, low=2, turnover=20),
    ]
    table = usd.USD(
        day=date(2025, 1, 27),
        rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(42)),
        df=[],
    )
    table.update(update_day, rows)
    assert table.day == update_day

    assert table.df == rows


def test_usd_update_with_df():
    update_day = date(2025, 1, 29)
    rows = [
        usd.Row(day=date(2025, 1, 28), open=2, close=3, high=4, low=2, turnover=20),
        usd.Row(day=date(2025, 1, 29), open=3, close=4, high=5, low=3, turnover=30),
    ]
    table = usd.USD(
        day=date(2025, 1, 28),
        rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(42)),
        df=[
            usd.Row(day=date(2025, 1, 27), open=1, close=2, high=3, low=1, turnover=10),
            usd.Row(day=date(2025, 1, 28), open=2, close=3, high=4, low=2, turnover=20),
        ],
    )
    table.update(update_day, rows)
    assert table.day == update_day

    assert table.df == [
        usd.Row(day=date(2025, 1, 27), open=1, close=2, high=3, low=1, turnover=10),
        usd.Row(day=date(2025, 1, 28), open=2, close=3, high=4, low=2, turnover=20),
        usd.Row(day=date(2025, 1, 29), open=3, close=4, high=5, low=3, turnover=30),
    ]


def test_usd_update_mismatch():
    update_day = date(2025, 1, 29)
    rows = [
        usd.Row(day=date(2025, 1, 28), open=9, close=9, high=9, low=9, turnover=9),
        usd.Row(day=date(2025, 1, 29), open=3, close=4, high=5, low=3, turnover=30),
    ]
    table = usd.USD(
        day=date(2025, 1, 28),
        rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(42)),
        df=[
            usd.Row(day=date(2025, 1, 27), open=1, close=2, high=3, low=1, turnover=10),
            usd.Row(day=date(2025, 1, 28), open=2, close=3, high=4, low=2, turnover=20),
        ],
    )
    with pytest.raises(errors.DomainError, match="data mismatch"):
        table.update(update_day, rows)


def test_usd_last_row_date():
    table = usd.USD(
        day=date(2025, 1, 27),
        rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(42)),
        df=[
            usd.Row(day=date(2025, 1, 27), open=1, close=2, high=3, low=1, turnover=10),
            usd.Row(day=date(2025, 1, 28), open=2, close=3, high=4, low=2, turnover=20),
        ],
    )
    assert table.last_row_date() == date(2025, 1, 28)


def test_usd_last_row_date_no_df():
    table = usd.USD(
        day=date(2025, 1, 27),
        rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(42)),
        df=[],
    )
    assert table.last_row_date() is None
