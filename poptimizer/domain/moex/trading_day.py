from pydantic import Field, PositiveInt, field_validator

from poptimizer import consts
from poptimizer.domain import domain


class TradingDay(domain.Entity):
    tickers: tuple[domain.Ticker, ...] = Field(default_factory=tuple)
    trading_days: list[domain.Day] = Field(default_factory=list)
    forecast_days: PositiveInt = consts.FORECAST_DAYS

    _sorted_tickers = field_validator("tickers")(domain.sorted_tickers_validator)
    _sorted_trading_days = field_validator("trading_days")(domain.sorted_days_validator)

    def update_last_check(self, day: domain.Day) -> None:
        self.day = day

    def update_last_trading_day(
        self,
        tickers: tuple[domain.Ticker, ...],
        trading_days: list[domain.Day],
        forecast_days: int,
    ) -> None:
        self.day = trading_days[-1]
        self.tickers = tickers
        self.trading_days = trading_days
        self.forecast_days = forecast_days
