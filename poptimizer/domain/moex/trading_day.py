from pydantic import Field, PositiveInt, field_validator

from poptimizer import consts
from poptimizer.domain import domain


class TradingDay(domain.Entity):
    last: domain.Day = consts.START_DAY
    tickers: tuple[domain.Ticker, ...] = Field(default_factory=tuple)
    forecast_days: PositiveInt = 1

    _sorted_tickers = field_validator("tickers")(domain.sorted_tickers_validator)

    def update_last_check(self, day: domain.Day) -> None:
        self.day = day

    def update_last_trading_day(
        self,
        day: domain.Day,
        tickers: tuple[domain.Ticker, ...],
        forecast_days: int,
    ) -> None:
        self.day = day
        self.last = day
        self.tickers = tickers
        self.forecast_days = forecast_days
