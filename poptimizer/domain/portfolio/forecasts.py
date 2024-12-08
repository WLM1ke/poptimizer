import itertools
from typing import Annotated

from pydantic import BaseModel, Field, NonNegativeFloat, NonNegativeInt, PlainSerializer, field_validator

from poptimizer.domain import domain


class Position(BaseModel):
    ticker: domain.Ticker
    mean: float = 0
    std: NonNegativeFloat = 0
    beta: float = 0
    grad: float = 0


class Forecast(domain.Entity):
    models: Annotated[
        set[domain.UID],
        PlainSerializer(
            list,
            return_type=list,
        ),
    ] = Field(default_factory=set)
    forecasts: NonNegativeInt = 0
    portfolio_ver: domain.Version = domain.Version(0)
    portfolio: Position = Field(default_factory=lambda: Position(ticker=domain.PortfolioTicker))
    cash: Position = Field(default_factory=lambda: Position(ticker=domain.CashTicker))
    positions: list[Position] = Field(default_factory=list)

    @field_validator("positions")
    def _sorted_by_tickers(cls, positions: list[Position]) -> list[Position]:
        positions_pairs = itertools.pairwise(positions)

        if not all(cur.ticker < next_.ticker for cur, next_ in positions_pairs):
            raise ValueError("tickers are not sorted")

        return positions

    def init_day(self, day: domain.Day) -> None:
        self.models.clear()
        self.forecasts = 0
        self.day = day
