from datetime import date, datetime
from typing import Annotated, NewType, Protocol

from pydantic import BaseModel, ConfigDict, PlainSerializer

UID = NewType("UID", str)
Version = NewType("Version", int)
Subdomain = NewType("Subdomain", str)
Component = NewType("Component", str)


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


class Entity(BaseModel):
    rev: Revision
    timestamp: Day

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


class ErrorEvent(Event):
    component: Component
    err: str


class Response(Message):
    ...


class Request[T: Response](Message):
    ...


class Ctx(Protocol):
    async def get[E: Entity](self, t_entity: type[E], uid: UID | None = None, *, for_update: bool = True) -> E:
        ...

    def publish(self, event: Event) -> None:
        ...

    def publish_err(self, err: str) -> None:
        ...

    async def request[R: Response](self, request: Request[R]) -> R:
        ...
