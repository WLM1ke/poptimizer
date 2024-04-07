from datetime import date, datetime
from typing import Annotated, Any, NewType, Protocol

from pydantic import BaseModel, ConfigDict, PlainSerializer

UID = NewType("UID", str)
Version = NewType("Version", int)


def get_component_name(component: Any) -> str:
    return component.__class__.__name__


def get_component_name_for_type(component_type: type[Any]) -> str:
    return component_type.__name__


class Revision(BaseModel):
    uid: UID
    ver: Version

    model_config = ConfigDict(frozen=True)


Day = Annotated[
    date,
    PlainSerializer(
        lambda date: datetime(
            year=date.year,
            month=date.month,
            day=date.day,
        ),
        return_type=datetime,
    ),
]


class State(BaseModel): ...


class Entity(BaseModel):
    rev: Revision
    day: Day

    @property
    def uid(self) -> UID:
        return self.rev.uid

    @property
    def ver(self) -> Version:
        return self.rev.ver


class Ctx(Protocol):
    async def get[E: Entity](
        self,
        t_entity: type[E],
        uid: UID | None = None,
        *,
        for_update: bool = True,
    ) -> E: ...
    def info(self, msg: str) -> None: ...
    def warn(self, msg: str) -> None: ...
