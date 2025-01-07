from pydantic import Field, PositiveInt

from poptimizer import consts
from poptimizer.domain import domain


class TradingDay(domain.Entity):
    last_check: domain.Day = consts.START_DAY
    positions: domain.Positions = Field(repr=False)
    forecast_days: PositiveInt

    def update_last_check(self, day: domain.Day) -> None:
        self.last_check = day

    def update_last_trading_day(
        self,
        day: domain.Day,
        positions: domain.Positions,
        forecast_days: int,
    ) -> None:
        self.day = day
        self.last_check = day
        self.positions = positions
        self.forecast_days = forecast_days
