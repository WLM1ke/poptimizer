from datetime import date, datetime
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, PlainSerializer


class Revision(BaseModel):
    uid: str
    ver: int

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
    def uid(self) -> str:
        return self.rev.uid

    @property
    def ver(self) -> int:
        return self.rev.ver


class Message(BaseModel):
    model_config = ConfigDict(frozen=True)


class Event(Message):
    """Событие.

    Сообщение, которое могут принять 0 или несколько получателей - не предполагает ответа.
    Собственником события является тот, кто его производит.
    """


class Response(Message):
    """Ответ.

    Сообщение, которое поступает в ответ на запрос.
    Собственником события является его единственный получатель запроса.
    """


TResponse = TypeVar("TResponse", bound=Response)


class Request(Message, Generic[TResponse]):
    """Запрос.

    Сообщение, которое может принять 1 получатель - предполагает ответ.
    Собственником события является его единственный получатель.
    """
