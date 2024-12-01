import itertools
from typing import Annotated, Self

from pydantic import Field, PlainSerializer, field_validator, model_validator

from poptimizer.domain import domain


def _must_be_sorted_by_ticker(tickers: tuple[str, ...]) -> tuple[str, ...]:
    ticker_pairs = itertools.pairwise(tickers)

    if not all(ticker < next_ for ticker, next_ in ticker_pairs):
        raise ValueError("tickers are not sorted")

    return tickers


class Forecast(domain.Entity):
    tickers: tuple[str, ...] = Field(default_factory=tuple)
    mean: list[list[float]] = Field(default_factory=list)
    cov: list[list[float]] = Field(default_factory=list)
    risk_tolerance: float = Field(0, ge=0, le=1)

    _must_be_sorted_by_ticker = field_validator("tickers")(_must_be_sorted_by_ticker)

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


class PortForecast(domain.Entity):
    tickers: tuple[str, ...] = Field(default_factory=tuple)
    forecasts: Annotated[
        set[domain.UID],
        PlainSerializer(lambda x: list(x), return_type=list),
    ] = Field(default_factory=set)

    _must_be_sorted_by_ticker = field_validator("tickers")(_must_be_sorted_by_ticker)

    def init_day(
        self,
        day: domain.Day,
        tickers: tuple[str, ...],
        uid: domain.UID,
    ) -> None:
        self.day = day
        self.tickers = tickers
        self.forecasts = {uid}

    def is_new_uid(self, uid: domain.UID) -> bool:
        if uid in self.forecasts:
            return False

        self.forecasts.add(uid)

        return True
