from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    FiniteFloat,
    NonNegativeFloat,
    PlainSerializer,
    PositiveInt,
)

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
    portfolio_ver: domain.Version = domain.Version(0)
    forecast_days: PositiveInt = 1
    forecasts_count: PositiveInt = 1
    positions: Annotated[
        list[Position],
        AfterValidator(domain.sorted_with_ticker_field_validator),
    ] = Field(default_factory=list)
    risk_tolerance: float = Field(0, ge=0, le=1)
    mean: float = 0
    std: float = 0

    def init_day(self, day: domain.Day) -> None:
        self.day = day
        self.models.clear()

    def update_required(self, portfolio_ver: domain.Version) -> bool:
        if len(self.models) <= 1:
            return False

        if portfolio_ver > self.portfolio_ver:
            return True

        return len(self.models) ** 0.5 - self.forecasts_count**0.5 >= 1
