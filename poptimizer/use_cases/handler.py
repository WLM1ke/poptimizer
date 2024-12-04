from typing import Protocol

from pydantic import BaseModel

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
    day: domain.Day


class NewDataPublished(Event):
    day: domain.Day


class IndexesUpdated(Event):
    day: domain.Day


class SecuritiesUpdated(Event):
    day: domain.Day


class QuotesUpdated(Event):
    day: domain.Day


class DivUpdated(Event):
    day: domain.Day


class PortfolioUpdated(Event):
    day: domain.Day


class DivStatusUpdated(Event):
    day: domain.Day


class DataUpdated(Event):
    day: domain.Day


class EvolutionStepFinished(Event):
    day: domain.Day


class ForecastCreated(Event):
    day: domain.Day
