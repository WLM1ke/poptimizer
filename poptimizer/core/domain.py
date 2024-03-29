from datetime import date, datetime
from enum import StrEnum, auto, unique
from typing import Annotated, Any, NewType, Protocol

from pydantic import BaseModel, ConfigDict, PlainSerializer

UID = NewType("UID", str)
Version = NewType("Version", int)
Subdomain = NewType("Subdomain", str)
Component = NewType("Component", str)


def get_component_name(component: Any) -> Component:
    return Component(component.__class__.__name__)


def get_component_name_for_type(component_type: type[Any]) -> Component:
    return Component(component_type.__name__)


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

Ticker = NewType("Ticker", str)


@unique
class Currency(StrEnum):
    RUR = auto()
    USD = auto()


class Entity(BaseModel):
    rev: Revision
    day: Day

    @property
    def uid(self) -> UID:
        return self.rev.uid

    @property
    def ver(self) -> Version:
        return self.rev.ver


class Message(BaseModel):
    model_config = ConfigDict(frozen=True)


class Event(Message):
    ...


class WarningEvent(Event):
    component: Component
    msg: str


class Response(Message):
    ...


class Request[T: Response](Message):
    ...


class Ctx(Protocol):
    async def get[E: Entity](self, t_entity: type[E], uid: UID | None = None, *, for_update: bool = True) -> E:
        ...

    def publish(self, event: Event) -> None:
        ...

    def warn(self, msg: str) -> None:
        ...

    async def request[R: Response](self, request: Request[R]) -> R:
        ...


class SrvCtx(Protocol):
    def publish(self, event: Event) -> None:
        ...

    async def request[R: Response](self, request: Request[R]) -> R:
        ...
