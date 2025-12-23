from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Protocol

import aiohttp
from pydantic import BaseModel, Field, ValidationError, computed_field

from poptimizer import errors
from poptimizer.domain import domain


class Event(BaseModel): ...


class Ctx(Protocol):
    def publish(self, msg: Event) -> None: ...
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


class MigrationFinished(Event): ...


class NewDataPublished(Event):
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


class IndexesUpdated(Event):
    trading_days: domain.TradingDays = Field(repr=False)

    @property
    def day(self) -> domain.Day:
        return self.trading_days[-1]


class PortfolioUpdated(Event):
    trading_days: domain.TradingDays = Field(repr=False)

    @computed_field
    @property
    def day(self) -> domain.Day:
        return self.trading_days[-1]


class QuotesFeatUpdated(Event):
    trading_days: domain.TradingDays = Field(repr=False)

    @computed_field
    @property
    def day(self) -> domain.Day:
        return self.trading_days[-1]


class IndexFeatUpdated(Event):
    trading_days: domain.TradingDays = Field(repr=False)

    @computed_field
    @property
    def day(self) -> domain.Day:
        return self.trading_days[-1]


class DayFeatUpdated(Event):
    day: domain.Day


class SecFeatUpdated(Event):
    day: domain.Day


class DivStatusUpdated(Event):
    day: domain.Day


class DataChecked(Event):
    day: domain.Day


class ModelDeleted(Event):
    day: domain.Day
    uid: domain.UID


class ModelEvaluated(Event):
    day: domain.Day
    uid: domain.UID


class ForecastsAnalyzed(Event):
    day: domain.Day


@asynccontextmanager
async def wrap_http_err(msg: str) -> AsyncIterator[None]:
    try:
        yield
    except (TimeoutError, aiohttp.ClientError) as err:
        raise errors.UseCasesError(msg) from err


@contextmanager
def wrap_validation_err(msg: str) -> Iterator[None]:
    try:
        yield
    except ValidationError as err:
        raise errors.UseCasesError(msg) from err
