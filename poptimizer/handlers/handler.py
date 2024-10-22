from typing import Protocol

from pydantic import BaseModel

from poptimizer import consts
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


class TradingDayFinished(Msg):
    day: domain.Day


class DataUpdateFinished(Msg):
    day: domain.Day


class EvolutionStepFinished(Msg):
    day: domain.Day = consts.START_DAY
