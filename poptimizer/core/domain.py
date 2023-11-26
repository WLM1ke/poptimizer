from datetime import date, datetime
from typing import Annotated, NewType, Protocol

from pydantic import BaseModel, ConfigDict, PlainSerializer

UID = NewType("UID", str)
Version = NewType("Version", int)
Subdomain = NewType("Subdomain", str)


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
    """Событие.

    Сообщение, которое могут принять 0 или несколько получателей - не предполагает ответа.
    Собственником события является тот, кто его производит.
    """


class Response(Message):
    """Ответ на запрос.

    Сообщение, которое поступает в ответ на запрос.
    Собственником события является его единственный получатель запроса.
    """


class Request[T: Response](Message):
    """Запрос.

    Сообщение, которое может принять 1 получатель - предполагает ответ.
    Собственником события является его единственный получатель.
    """


class Ctx(Protocol):
    async def get[E: Entity](self, t_entity: type[E], uid: UID, *, for_update: bool = True) -> E:
        ...

    def publish(self, event: Event) -> None:
        ...

    async def request[R: Response](self, request: Request[R]) -> R:
        ...
