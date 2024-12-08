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
    mean: float
    std: float
    positions: list[Position] = Field(default_factory=list)

    _must_be_sorted_by_ticker = field_validator("positions")(domain.sorted_with_ticker_field)

    def init_day(self, day: domain.Day) -> None:
        self.models.clear()
        self.forecasts = 0
        self.day = day
