import itertools
from datetime import date, datetime
from enum import StrEnum, auto, unique
from typing import Annotated, Final, NewType, Protocol

from pydantic import AfterValidator, BaseModel, ConfigDict, PlainSerializer

from poptimizer import consts

UID = NewType("UID", str)
Version = NewType("Version", int)


class Revision(BaseModel):
    uid: UID
    ver: Version

    model_config = ConfigDict(frozen=True)


Day = Annotated[
    date,
    PlainSerializer(
        lambda date: datetime(
            year=date.year,
            month=date.month,
            day=date.day,
        ),
        return_type=datetime,
    ),
]

Ticker = NewType("Ticker", str)
CashTicker: Final = Ticker("CASH")

AccName = NewType("AccName", str)


@unique
class Currency(StrEnum):
    RUR = auto()
    USD = auto()


class Entity(BaseModel):
    rev: Revision
    day: Day

    @property
    def uid(self) -> UID:
        return self.rev.uid

    @property
    def ver(self) -> Version:
        return self.rev.ver


class Row(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class _RowWithDate(Protocol):
    day: Day


def sorted_by_day_validator(df: list[_RowWithDate]) -> list[_RowWithDate]:
    dates_pairs = itertools.pairwise(row.day for row in df)

    if not all(day < next_ for day, next_ in dates_pairs):
        raise ValueError("df not sorted by day")

    return df


def after_start_date_validator(df: list[_RowWithDate]) -> list[_RowWithDate]:
    if df and (day := df[0].day) < consts.START_DAY:
        raise ValueError(f"day before start day {day}")

    return df


def _sorted_days_validator(days: list[Day]) -> list[Day]:
    day_pairs = itertools.pairwise(days)

    if not all(day < next_ for day, next_ in day_pairs):
        raise ValueError("days are not sorted")

    return days


TradingDays = Annotated[list[Day], AfterValidator(_sorted_days_validator)]


def _sorted_tickers_validator(tickers: tuple[Ticker, ...]) -> tuple[Ticker, ...]:
    ticker_pairs = itertools.pairwise(tickers)

    if not all(ticker < next_ for ticker, next_ in ticker_pairs):
        raise ValueError("tickers are not sorted")

    return tickers


Tickers = Annotated[tuple[Ticker, ...], AfterValidator(_sorted_tickers_validator)]


class WithTickerField(Protocol):
    ticker: Ticker


def sorted_with_ticker_field_validator(rows: list[WithTickerField]) -> list[WithTickerField]:
    ticker_pairs = itertools.pairwise(row.ticker for row in rows)

    if not all(ticker < next_ for ticker, next_ in ticker_pairs):
        raise ValueError("tickers are not sorted")

    return rows
