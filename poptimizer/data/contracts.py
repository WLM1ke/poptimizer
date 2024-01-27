import itertools
from enum import StrEnum, auto

from pydantic import BaseModel, Field, NonNegativeFloat, PositiveFloat, PositiveInt, field_validator

from poptimizer.core import domain
from poptimizer.data import data


class QuotesUpdated(domain.Event):
    day: domain.Day


class Security(BaseModel):
    lot: PositiveInt
    price: PositiveFloat
    turnover: NonNegativeFloat


class SecData(domain.Response):
    securities: dict[domain.Ticker, Security]


class GetSecData(domain.Request[SecData]):
    day: domain.Day


class DivTickers(domain.Response):
    tickers: list[domain.Ticker]


class GetDivTickers(domain.Request[DivTickers]):
    ...


class DivCompStatus(StrEnum):
    EXTRA = auto()
    OK = auto()
    MISSED = auto()


class DivCompareRow(data.Row):
    day: domain.Day
    dividend: float = Field(gt=0)
    currency: domain.Currency
    status: DivCompStatus

    def to_tuple(self) -> tuple[domain.Day, float, domain.Currency]:
        return self.day, self.dividend, self.currency


class DividendsData(domain.Response):
    dividends: list[DivCompareRow]

    @field_validator("dividends")
    def _sorted_by_date_div_currency(cls, dividends: list[DivCompareRow]) -> list[DivCompareRow]:
        day_pairs = itertools.pairwise(row.to_tuple() for row in dividends)

        if not all(day < next_ for day, next_ in day_pairs):
            raise ValueError("raw dividends are not sorted")

        return dividends


class GetDividends(domain.Request[DividendsData]):
    ticker: domain.Ticker
