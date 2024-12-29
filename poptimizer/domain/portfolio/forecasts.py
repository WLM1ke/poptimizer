from typing import Annotated

from pydantic import BaseModel, Field, FiniteFloat, NonNegativeFloat, PlainSerializer, PositiveInt, field_validator

from poptimizer.domain import domain


class Position(BaseModel):
    ticker: domain.Ticker
    weight: NonNegativeFloat
    mean: FiniteFloat
    std: NonNegativeFloat
    beta: FiniteFloat
    grad: FiniteFloat
    grad_lower: FiniteFloat
    grad_upper: FiniteFloat


class Forecast(domain.Entity):
    models: Annotated[
        set[domain.UID],
        PlainSerializer(
            list,
            return_type=list,
        ),
    ] = Field(default_factory=set)
    forecasts_count: PositiveInt = 1
    portfolio_ver: domain.Version = domain.Version(0)
    risk_tolerance: float = Field(0, ge=0, le=1)
    mean: float = 0
    std: float = 0
    positions: list[Position] = Field(default_factory=list)

    _must_be_sorted_by_ticker = field_validator("positions")(domain.sorted_with_ticker_field_validator)

    def init_day(self, day: domain.Day) -> None:
        self.models.clear()
        self.forecasts_count = 1
        self.day = day
