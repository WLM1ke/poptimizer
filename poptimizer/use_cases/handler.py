from typing import Protocol

from pydantic import BaseModel

from poptimizer.domain import domain


class Msg(BaseModel): ...


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


class AppStarted(Msg): ...


class DataChecked(Msg): ...


class NewDataPublished(Msg):
    day: domain.Day


class IndexesUpdated(Msg):
    day: domain.Day


class SecuritiesUpdated(Msg):
    day: domain.Day


class QuotesUpdated(Msg):
    day: domain.Day


class DivUpdated(Msg):
    day: domain.Day


class PortfolioUpdated(Msg):
    day: domain.Day


class DivStatusUpdated(Msg):
    day: domain.Day


class DataUpdated(Msg):
    day: domain.Day


class EvolutionStepFinished(Msg): ...
