from typing import Protocol

from pydantic import BaseModel, Field, PositiveInt, field_validator

from poptimizer.domain import domain


class Msg(BaseModel): ...


class Event(Msg): ...


class DTO(Msg): ...


class Ctx(Protocol):
    async def get[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E: ...

    async def get_for_update[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E: ...


class AppStarted(Event): ...


class NewDataPublished(Event):
    day: domain.Day


class IndexesUpdated(Event):
    day: domain.Day


class SecuritiesUpdated(Event):
    day: domain.Day


class DivUpdated(Event):
    day: domain.Day


class QuotesUpdated(Event):
    trading_days: domain.TradingDays = Field(repr=False)

    @property
    def day(self) -> domain.Day:
        return self.trading_days[-1]


class PortfolioUpdated(Event):
    tickers: tuple[domain.Ticker, ...] = Field(repr=False)
    trading_days: domain.TradingDays = Field(repr=False)
    forecast_days: PositiveInt

    @property
    def day(self) -> domain.Day:
        return self.trading_days[-1]

    _sorted_tickers = field_validator("tickers")(domain.sorted_tickers_validator)


class QuotesFeatUpdated(Event):
    tickers: tuple[domain.Ticker, ...] = Field(repr=False)
    trading_days: domain.TradingDays = Field(repr=False)
    forecast_days: PositiveInt

    @property
    def day(self) -> domain.Day:
        return self.trading_days[-1]

    _sorted_tickers = field_validator("tickers")(domain.sorted_tickers_validator)


class DivStatusUpdated(Event):
    day: domain.Day


class DataChecked(Event):
    day: domain.Day
    tickers: tuple[domain.Ticker, ...] = Field(repr=False)
    forecast_days: PositiveInt

    _sorted_tickers = field_validator("tickers")(domain.sorted_tickers_validator)


class ModelDeleted(Event):
    day: domain.Day
    uid: domain.UID


class ModelEvaluated(Event):
    day: domain.Day
    uid: domain.UID


class ForecastsAnalyzed(Event):
    day: domain.Day
