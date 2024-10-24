import itertools

from pydantic import Field, field_validator

from poptimizer.domain import domain
from poptimizer.domain.div import raw


class Row(domain.Row):
    ticker: domain.Ticker
    ticker_base: str
    preferred: bool
    day: domain.Day


class DivStatus(domain.Entity):
    df: list[Row] = Field(default_factory=list[Row])

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

    @field_validator("df")
    def _must_be_sorted_by_ticker_and_day(cls, df: list[Row]) -> list[Row]:
        ticker_date_pairs = itertools.pairwise((row.ticker, row.day) for row in df)

        if not all(ticker_date <= next_ for ticker_date, next_ in ticker_date_pairs):
            raise ValueError("ticker and dates are not sorted")

        return df
