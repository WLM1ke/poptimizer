from typing import Annotated, Final

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

_MINIMAL_FORECASTS_AMOUNT: Final = 4


class Position(BaseModel):
    ticker: domain.Ticker
    weight: NonNegativeFloat
    mean: FiniteFloat
    std: NonNegativeFloat
    beta: FiniteFloat
    grad: FiniteFloat
    grad_lower: float
    grad_upper: float
    accounts: list[domain.AccName]


class Forecast(domain.Entity):
    models: Annotated[
        set[domain.UID],
        PlainSerializer(
            list,
            return_type=list,
        ),
    ] = Field(default_factory=set[domain.UID])
    portfolio_ver: domain.Version = domain.Version(0)
    forecast_days: PositiveInt = 1
    forecasts_count: PositiveInt = 1
    positions: Annotated[
        list[Position],
        AfterValidator(domain.sorted_with_ticker_field_validator),
    ] = Field(default_factory=list[Position])
    risk_tolerance: float = Field(0, ge=0, le=1)
    mean: FiniteFloat = 0
    std: NonNegativeFloat = 0
    illiquid: Annotated[
        set[domain.Ticker],
        PlainSerializer(
            list,
            return_type=list,
        ),
    ] = Field(default_factory=set[domain.Ticker])

    def init_day(self, day: domain.Day) -> None:
        self.day = day
        self.models.clear()

    def update_required(self, portfolio_ver: domain.Version) -> bool:
        if len(self.models) < _MINIMAL_FORECASTS_AMOUNT:
            return False

        if portfolio_ver > self.portfolio_ver:
            return True

        return abs(len(self.models) ** 0.5 - self.forecasts_count**0.5) >= 1

    def buy_sell(self) -> tuple[float, list[Position], list[Position]]:
        buy = sorted(
            (pos for pos in self.positions if pos.ticker not in self.illiquid),
            key=lambda pos: pos.grad_lower,
            reverse=True,
        )
        sell = sorted((pos for pos in self.positions if pos.accounts), key=lambda pos: pos.grad_upper)

        for i, (b, s) in enumerate(zip(buy, sell, strict=False)):
            if b.grad_lower < s.grad_upper:
                if i == 0:
                    break

                sell = sell[i - 1 :: -1]
                buy = buy[: i + (buy[i].grad_lower > sell[0].grad_upper)]
                breakeven = (buy[-1].grad_lower + sell[0].grad_upper) / 2

                return breakeven, buy, sell

        return buy[0].grad_lower, buy[:1], []
