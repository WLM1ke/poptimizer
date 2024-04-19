import bisect
import itertools
import re
from typing import Final

from pydantic import Field, field_validator

from poptimizer.core import domain
from poptimizer.data import data

_URL: Final = "https://web.moex.com/moex-web-icdb-api/api/v1/export/site-register-closings/csv?separator=1&language=1"
_LOOK_BACK_DAYS: Final = 14
_DATE_FMT: Final = "%m/%d/%Y %H:%M:%S"
_RE_TICKER = re.compile(r", ([A-Z]+-[A-Z]+|[A-Z]+) \[")


class RowRaw(data.Row):
    day: domain.Day
    dividend: float = Field(gt=0)
    currency: domain.Currency

    def to_tuple(self) -> tuple[domain.Day, float, domain.Currency]:
        return self.day, self.dividend, self.currency


class DivRaw(domain.Entity):
    df: list[RowRaw] = Field(default_factory=list[RowRaw])

    def update(self, update_day: domain.Day, rows: list[RowRaw]) -> None:
        self.day = update_day

        rows.sort(key=lambda row: row.to_tuple())

        self.df = rows

    def has_day(self, day: domain.Day) -> bool:
        pos = bisect.bisect_left(self.df, day, key=lambda row: row.day)

        return pos != len(self.df) and self.df[pos].day == day

    def has_row(self, row: RowRaw) -> bool:
        pos = bisect.bisect_left(
            self.df,
            row.to_tuple(),
            key=lambda row: row.to_tuple(),
        )

        return pos != len(self.df) and row == self.df[pos]

    @field_validator("df")
    def _sorted_by_date_div_currency(cls, df: list[RowRaw]) -> list[RowRaw]:
        day_pairs = itertools.pairwise(row.to_tuple() for row in df)

        if not all(day <= next_ for day, next_ in day_pairs):
            raise ValueError("raw dividends are not sorted")

        return df


class RowStatus(data.Row):
    ticker: domain.Ticker
    ticker_base: str
    preferred: bool
    day: domain.Day


class DivStatus(domain.Entity):
    df: list[RowStatus] = Field(default_factory=list[RowStatus])

    def update(self, update_day: domain.Day, rows: list[RowStatus]) -> None:
        self.day = update_day
        rows.sort(key=lambda status: (status.ticker, status.day))
        self.df = rows

    @field_validator("df")
    def _must_be_sorted_by_ticker_and_day(cls, df: list[RowStatus]) -> list[RowStatus]:
        ticker_date_pairs = itertools.pairwise((row.ticker, row.day) for row in df)

        if not all(ticker_date <= next_ for ticker_date, next_ in ticker_date_pairs):
            raise ValueError("ticker and dates are not sorted")

        return df
