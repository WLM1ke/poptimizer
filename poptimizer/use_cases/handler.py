from typing import Protocol

from pydantic import BaseModel, Field, computed_field

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
    trading_days: domain.TradingDays = Field(repr=False)

    @computed_field
    def day(self) -> domain.Day:
        return self.trading_days[-1]


class QuotesFeatUpdated(Event):
    day: domain.Day


class DivStatusUpdated(Event):
    day: domain.Day


class DataChecked(Event):
    day: domain.Day
    portfolio_ver: domain.Version


class ModelDeleted(Event):
    day: domain.Day
    portfolio_ver: domain.Version
    uid: domain.UID


class ModelEvaluated(Event):
    day: domain.Day
    portfolio_ver: domain.Version
    uid: domain.UID


class ForecastsAnalyzed(Event):
    day: domain.Day
    portfolio_ver: domain.Version
