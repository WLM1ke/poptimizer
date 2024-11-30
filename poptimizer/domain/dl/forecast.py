import itertools
from typing import Self

from pydantic import Field, field_validator, model_validator

from poptimizer.domain import domain


class Forecast(domain.Entity):
    tickers: tuple[str, ...]
    mean: list[float]
    cov: list[list[float]]
    risk_tolerance: float = Field(ge=0, le=1)

    @field_validator("tickers")
    def _must_be_sorted_by_ticker(cls, tickers: tuple[str, ...]) -> tuple[str, ...]:
        ticker_pairs = itertools.pairwise(tickers)

        if not all(ticker < next_ for ticker, next_ in ticker_pairs):
            raise ValueError("tickers are not sorted")

        return tickers

    @model_validator(mode="after")
    def _match_length(self) -> Self:
        n = len(self.tickers)
        if len(self.mean) != n:
            raise ValueError("invalid mean length")

        if any(len(row) != n for row in self.cov):
            raise ValueError("invalid cov length")

        return self
