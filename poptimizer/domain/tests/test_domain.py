from datetime import date, datetime, timedelta

import pytest
from pydantic import BaseModel, ValidationError

from poptimizer import consts
from poptimizer.domain import domain


@pytest.fixture
def revision():
    return domain.Revision(uid=domain.UID("uid"), ver=domain.Version(0))


def test_revision(revision: domain.Revision) -> None:
    with pytest.raises(ValidationError, match="Instance is frozen"):
        revision.ver = domain.Version(1)


def test_entity(revision: domain.Revision) -> None:
    entity = domain.Entity(rev=revision, day=date(2024, 12, 29))

    assert entity.uid == revision.uid
    assert entity.ver == revision.ver

    assert entity.model_dump().pop("day") == datetime(2024, 12, 29)


class _TestDayRow(BaseModel):
    day: domain.Day


@pytest.mark.parametrize(
    ("rows", "err"),
    [
        ([], False),
        ([_TestDayRow(day=date(2024, 12, 29))], False),
        ([_TestDayRow(day=date(2024, 12, 29)), _TestDayRow(day=date(2024, 12, 31))], False),
        ([_TestDayRow(day=date(2024, 12, 29)), _TestDayRow(day=date(2024, 12, 29))], True),
        ([_TestDayRow(day=date(2024, 12, 29)), _TestDayRow(day=date(2024, 12, 28))], True),
    ],
)
def test_sorted_by_day_validator(rows: list[_TestDayRow], *, err: bool) -> None:
    if not err:
        assert rows == domain.sorted_by_day_validator(rows)

        return

    with pytest.raises(ValueError, match="df not sorted by day"):
        domain.sorted_by_day_validator(rows)


@pytest.mark.parametrize(
    ("rows", "err"),
    [
        ([], False),
        ([_TestDayRow(day=consts.START_DAY)], False),
        ([_TestDayRow(day=consts.START_DAY - timedelta(days=1))], True),
    ],
)
def test_after_start_date_validator(rows: list[_TestDayRow], *, err: bool) -> None:
    if not err:
        assert rows == domain.after_start_date_validator(rows)

        return

    with pytest.raises(ValueError, match="day before start day"):
        domain.after_start_date_validator(rows)


@pytest.mark.parametrize(
    ("tickers", "err"),
    [
        ([], False),
        ([domain.Ticker("GAZP")], False),
        ([domain.Ticker("GAZP"), domain.Ticker("LKOH")], False),
        ([domain.Ticker("GAZP"), domain.Ticker("AKRN")], True),
        ([domain.Ticker("GAZP"), domain.Ticker("GAZP")], True),
    ],
)
def test_sorted_tickers_validator(tickers: tuple[domain.Ticker, ...], *, err: bool) -> None:
    if not err:
        assert tickers == domain.sorted_tickers_validator(tickers)

        return

    with pytest.raises(ValueError, match="tickers are not sorted"):
        domain.sorted_tickers_validator(tickers)


@pytest.mark.parametrize(
    ("days", "err"),
    [
        ([], False),
        ([date(2025, 1, 5)], False),
        ([date(2025, 1, 5), date(2025, 1, 6)], False),
        ([date(2025, 1, 5), date(2025, 1, 5)], True),
        ([date(2025, 1, 5), date(2025, 1, 4)], True),
    ],
)
def test_sorted_days_validator(days: list[domain.Day], *, err: bool) -> None:
    if not err:
        assert days == domain.sorted_days_validator(days)

        return

    with pytest.raises(ValueError, match="days are not sorted"):
        domain.sorted_days_validator(days)


class _TestTickerRow(BaseModel):
    ticker: domain.Ticker


@pytest.mark.parametrize(
    ("tickers", "err"),
    [
        ([], False),
        ([_TestTickerRow(ticker=domain.Ticker("GAZP"))], False),
        ([_TestTickerRow(ticker=domain.Ticker("GAZP")), _TestTickerRow(ticker=domain.Ticker("LKOH"))], False),
        ([_TestTickerRow(ticker=domain.Ticker("GAZP")), _TestTickerRow(ticker=domain.Ticker("AKRN"))], True),
        ([_TestTickerRow(ticker=domain.Ticker("GAZP")), _TestTickerRow(ticker=domain.Ticker("GAZP"))], True),
    ],
)
def test_sorted_with_ticker_field_validator(tickers: list[_TestTickerRow], *, err: bool) -> None:
    if not err:
        assert tickers == domain.sorted_with_ticker_field_validator(tickers)

        return

    with pytest.raises(ValueError, match="tickers are not sorted"):
        domain.sorted_with_ticker_field_validator(tickers)
