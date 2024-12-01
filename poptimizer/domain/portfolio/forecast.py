import itertools
from typing import Self

from pydantic import Field, field_validator, model_validator

from poptimizer.domain import domain


class Forecast(domain.Entity):
    tickers: tuple[str, ...] = Field(default_factory=tuple)
    mean: list[list[float]] = Field(default_factory=list)
    cov: list[list[float]] = Field(default_factory=list)
    risk_tolerance: float = Field(0, ge=0, le=1)

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
            raise ValueError("invalid mean")

        if any(len(row) != 1 for row in self.mean):
            raise ValueError("invalid mean")

        if len(self.cov) != n:
            raise ValueError("invalid cov")

        if any(len(row) != n for row in self.cov):
            raise ValueError("invalid cov")

        return self
