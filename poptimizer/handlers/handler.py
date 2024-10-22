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

    def publish(self, msg: Msg) -> None: ...


class AppStarted(Msg): ...


class DataChecked(Msg): ...


class DataPublished(Msg):
    day: domain.Day


class IndexesUpdated(Msg):
    day: domain.Day


class DataUpdated(Msg):
    day: domain.Day


class EvolutionStepFinished(Msg): ...
