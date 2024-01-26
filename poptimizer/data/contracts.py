from pydantic import BaseModel, Field, NonNegativeFloat, PositiveFloat, PositiveInt

from poptimizer.core import consts, domain
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


class RawRow(data.Row):
    day: domain.Day
    dividend: float = Field(gt=0)
    currency: domain.Currency

    def to_tuple(self) -> tuple[domain.Day, float, domain.Currency]:
        return self.day, self.dividend, self.currency

    def is_valid_date(self) -> bool:
        return self.day >= consts.START_DAY


class DividendsData(domain.Response):
    saved: list[RawRow]
    compare: list[RawRow]


class GetDividends(domain.Request[DividendsData]):
    ticker: domain.Ticker
