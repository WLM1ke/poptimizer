from datetime import date, timedelta

import pytest

from poptimizer import consts, errors
from poptimizer.domain import domain
from poptimizer.domain.moex import quotes


def test_row_parse():
    row = quotes.Row.model_validate(
        {
            "begin": "2025-01-27",
            "open": 10.0,
            "close": 11.0,
            "high": 12.0,
            "low": 9.0,
            "value": 100.0,
        }
    )
    assert row.day == date(2025, 1, 27)
    assert row.open == 10.0
    assert row.close == 11.0
    assert row.high == 12.0
    assert row.low == 9.0
    assert row.turnover == 100.0


def test_row_invalid():
    for field in ["open", "close", "high", "low"]:
        data = {
            "begin": "2025-01-27",
            "open": 1.0,
            "close": 1.0,
            "high": 1.0,
            "low": 1.0,
            "value": 0.0,
        }
        data[field] = 0.0
        with pytest.raises(ValueError, match="greater than 0"):
            quotes.Row.model_validate(data)

    data = {
        "begin": "2025-01-27",
        "open": 1.0,
        "close": 1.0,
        "high": 1.0,
        "low": 1.0,
        "value": -1.0,
    }

    with pytest.raises(ValueError, match="greater than or equal to 0"):
        quotes.Row.model_validate(data)


def test_quotes_after_start_date_validator():
    row = quotes.Row(day=consts.START_DAY - timedelta(days=1), open=1.0, close=1.0, high=1.0, low=1.0, turnover=0.0)
    with pytest.raises(ValueError, match="day before start day"):
        quotes.Quotes(df=[row])


def test_quotes_sorted_validator():
    row1 = quotes.Row(day=date(2025, 1, 27), open=1.0, close=1.0, high=1.0, low=1.0, turnover=0.0)
    row2 = quotes.Row(day=date(2025, 1, 26), open=1.0, close=1.0, high=1.0, low=1.0, turnover=0.0)
    with pytest.raises(ValueError, match="not sorted by day"):
        quotes.Quotes(df=[row1, row2])


def test_quotes_update_no_df():
    update_day = date(2025, 1, 29)
    rows = [
        quotes.Row(day=date(2025, 1, 27), open=1.0, close=1.0, high=1.0, low=1.0, turnover=0.0),
        quotes.Row(day=date(2025, 1, 28), open=1.0, close=1.0, high=1.0, low=1.0, turnover=0.0),
    ]
    table = quotes.Quotes(
        day=date(2025, 1, 27), rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(42)), df=[]
    )
    table.update(update_day, rows)
    assert table.day == update_day
    assert table.df == rows


def test_quotes_update_with_df():
    update_day = date(2025, 1, 29)
    rows = [
        quotes.Row(day=date(2025, 1, 27), open=1.0, close=1.0, high=1.0, low=1.0, turnover=0.0),
        quotes.Row(day=date(2025, 1, 28), open=1.0, close=1.0, high=1.0, low=1.0, turnover=0.0),
    ]
    table = quotes.Quotes(
        day=date(2025, 1, 27),
        rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(42)),
        df=[
            quotes.Row(day=date(2025, 1, 26), open=1.0, close=1.0, high=1.0, low=1.0, turnover=0.0),
            quotes.Row(day=date(2025, 1, 27), open=1.0, close=1.0, high=1.0, low=1.0, turnover=0.0),
        ],
    )
    table.update(update_day, rows)
    assert table.day == update_day
    assert table.df == [
        quotes.Row(day=date(2025, 1, 26), open=1.0, close=1.0, high=1.0, low=1.0, turnover=0.0),
        quotes.Row(day=date(2025, 1, 27), open=1.0, close=1.0, high=1.0, low=1.0, turnover=0.0),
        quotes.Row(day=date(2025, 1, 28), open=1.0, close=1.0, high=1.0, low=1.0, turnover=0.0),
    ]


def test_quotes_update_mismatch():
    update_day = date(2025, 1, 29)
    rows = [
        quotes.Row(day=date(2025, 1, 27), open=2.0, close=1.0, high=1.0, low=1.0, turnover=0.0),
        quotes.Row(day=date(2025, 1, 28), open=1.0, close=1.0, high=1.0, low=1.0, turnover=0.0),
    ]
    table = quotes.Quotes(
        day=date(2025, 1, 27),
        rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(42)),
        df=[
            quotes.Row(day=date(2025, 1, 26), open=1.0, close=1.0, high=1.0, low=1.0, turnover=0.0),
            quotes.Row(day=date(2025, 1, 27), open=1.0, close=1.0, high=1.0, low=1.0, turnover=0.0),
        ],
    )
    with pytest.raises(errors.DomainError, match="data mismatch"):
        table.update(update_day, rows)


def test_quotes_last_row_date():
    table = quotes.Quotes(
        day=date(2025, 1, 27),
        rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(42)),
        df=[
            quotes.Row(day=date(2025, 1, 27), open=1.0, close=1.0, high=1.0, low=1.0, turnover=0.0),
            quotes.Row(day=date(2025, 1, 28), open=1.0, close=1.0, high=1.0, low=1.0, turnover=0.0),
        ],
    )
    assert table.last_row_date() == date(2025, 1, 28)


def test_quotes_last_row_date_no_df():
    table = quotes.Quotes(
        day=date(2025, 1, 27),
        rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(42)),
        df=[],
    )
    assert table.last_row_date() is None
