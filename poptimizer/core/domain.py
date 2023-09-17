from datetime import date, datetime
from typing import Annotated

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


class BaseEntity(BaseModel):
    rev: Revision
    timestamp: Day

    @property
    def uid(self) -> str:
        return self.rev.uid

    @property
    def ver(self) -> int:
        return self.rev.ver
