import itertools
from typing import Annotated

from pydantic import AfterValidator, Field

from poptimizer.domain import domain
from poptimizer.domain.div import raw


class Row(domain.Row):
    ticker: domain.Ticker
    ticker_base: str
    preferred: bool
    day: domain.Day


def _must_be_sorted_by_ticker_and_day(df: list[Row]) -> list[Row]:
    ticker_date_pairs = itertools.pairwise((row.ticker, row.day) for row in df)

    if not all(ticker_date <= next_ for ticker_date, next_ in ticker_date_pairs):
        raise ValueError("ticker and dates are not sorted")

    return df


class DivStatus(domain.Entity):
    df: Annotated[
        list[Row],
        AfterValidator(_must_be_sorted_by_ticker_and_day),
    ] = Field(default_factory=list[Row])

    def update(self, update_day: domain.Day, rows: list[Row]) -> None:
        self.day = update_day
        rows.sort(key=lambda status: (status.ticker, status.day))
        self.df = rows

    def filter(self, raw_table: raw.DivRaw) -> None:
        self.df = [
            status
            for status in self.df
            if not (status.ticker == domain.Ticker(raw_table.uid) and raw_table.has_day(status.day))
        ]
