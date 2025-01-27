from datetime import date

import pytest

from poptimizer import errors
from poptimizer.domain import domain
from poptimizer.domain.moex import index


def test_row_parse():
    assert index.Row(day=date(2025, 1, 27), close=1) == index.Row.model_validate(
        {
            "TRADEDATE": "2025-01-27",
            "CLOSE": 1,
        }
    )


def test_row_invalid():
    with pytest.raises(ValueError, match="Input should be greater than 0"):
        assert index.Row.model_validate(
            {
                "TRADEDATE": "2025-01-27",
                "CLOSE": -1,
            }
        )


def test_index_not_sorted_df():
    with pytest.raises(ValueError, match="Value error, df not sorted by day"):
        index.Index(
            day=date(2025, 1, 27),
            rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(42)),
            df=[
                index.Row(day=date(2025, 1, 27), close=1),
                index.Row(day=date(2025, 1, 27), close=2),
            ],
        )


def test_index_update_no_df():
    update_day = date(2025, 1, 29)
    rows = [
        index.Row(day=date(2025, 1, 27), close=1),
        index.Row(day=date(2025, 1, 28), close=2),
    ]
    table = index.Index(
        day=date(2025, 1, 27),
        rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(42)),
        df=[],
    )
    table.update(update_day, rows)

    assert table.day == update_day
    assert table.df == rows


def test_index_update_with_df():
    update_day = date(2025, 1, 29)
    rows = [
        index.Row(day=date(2025, 1, 27), close=1),
        index.Row(day=date(2025, 1, 28), close=2),
    ]
    table = index.Index(
        day=date(2025, 1, 27),
        rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(42)),
        df=[
            index.Row(day=date(2025, 1, 26), close=3),
            index.Row(day=date(2025, 1, 27), close=1),
        ],
    )
    table.update(update_day, rows)

    assert table.day == update_day
    assert table.df == [
        index.Row(day=date(2025, 1, 26), close=3),
        index.Row(day=date(2025, 1, 27), close=1),
        index.Row(day=date(2025, 1, 28), close=2),
    ]


def test_index_update_mismatch():
    update_day = date(2025, 1, 29)
    rows = [
        index.Row(day=date(2025, 1, 27), close=4),
        index.Row(day=date(2025, 1, 28), close=2),
    ]
    table = index.Index(
        day=date(2025, 1, 27),
        rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(42)),
        df=[
            index.Row(day=date(2025, 1, 26), close=3),
            index.Row(day=date(2025, 1, 27), close=1),
        ],
    )

    with pytest.raises(errors.DomainError, match="data mismatch"):
        table.update(update_day, rows)


def test_index_last_row_date():
    assert index.Index(
        day=date(2025, 1, 27),
        rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(42)),
        df=[
            index.Row(day=date(2025, 1, 27), close=1),
            index.Row(day=date(2025, 1, 28), close=2),
        ],
    ).last_row_date() == date(2025, 1, 28)


def test_index_last_row_date_no_df():
    assert (
        index.Index(
            day=date(2025, 1, 27),
            rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(42)),
            df=[],
        ).last_row_date()
        is None
    )
