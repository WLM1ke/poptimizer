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


class DataNotChanged(Event):
    tickers: tuple[domain.Ticker, ...] = Field(repr=False)
    trading_days: list[domain.Day] = Field(repr=False)
    forecast_days: PositiveInt

    @property
    def day(self) -> domain.Day:
        return self.trading_days[-1]

    _sorted_tickers = field_validator("tickers")(domain.sorted_tickers_validator)
    _sorted_trading_days = field_validator("trading_days")(domain.sorted_days_validator)


class NewDataPublished(Event):
    day: domain.Day


class IndexesUpdated(Event):
    day: domain.Day


class SecuritiesUpdated(Event):
    day: domain.Day


class DivUpdated(Event):
    day: domain.Day


class QuotesUpdated(Event):
    trading_days: list[domain.Day] = Field(repr=False)

    @property
    def day(self) -> domain.Day:
        return self.trading_days[-1]

    _sorted_trading_days = field_validator("trading_days")(domain.sorted_days_validator)


class PortfolioUpdated(Event):
    tickers: tuple[domain.Ticker, ...] = Field(repr=False)
    trading_days: list[domain.Day] = Field(repr=False)
    forecast_days: PositiveInt

    @property
    def day(self) -> domain.Day:
        return self.trading_days[-1]

    _sorted_tickers = field_validator("tickers")(domain.sorted_tickers_validator)
    _sorted_trading_days = field_validator("trading_days")(domain.sorted_days_validator)


class QuotesFeatUpdated(Event):
    tickers: tuple[domain.Ticker, ...] = Field(repr=False)
    trading_days: list[domain.Day] = Field(repr=False)
    forecast_days: PositiveInt

    @property
    def day(self) -> domain.Day:
        return self.trading_days[-1]

    _sorted_tickers = field_validator("tickers")(domain.sorted_tickers_validator)
    _sorted_trading_days = field_validator("trading_days")(domain.sorted_days_validator)


class PositionsUpdated(Event):
    day: domain.Day


class DivStatusUpdated(Event):
    day: domain.Day


class DataUpdated(Event):
    tickers: tuple[domain.Ticker, ...] = Field(repr=False)
    trading_days: list[domain.Day] = Field(repr=False)
    forecast_days: PositiveInt

    @property
    def day(self) -> domain.Day:
        return self.trading_days[-1]

    _sorted_tickers = field_validator("tickers")(domain.sorted_tickers_validator)
    _sorted_trading_days = field_validator("trading_days")(domain.sorted_days_validator)


class ModelDeleted(Event):
    day: domain.Day
    uid: domain.UID


class ModelEvaluated(Event):
    day: domain.Day
    uid: domain.UID


class ForecastsAnalyzed(Event):
    day: domain.Day
