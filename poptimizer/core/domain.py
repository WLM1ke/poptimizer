import itertools
import types
from datetime import date, datetime
from enum import StrEnum, auto, unique
from typing import Annotated, Any, NewType, Protocol

from pydantic import BaseModel, ConfigDict, PlainSerializer

from poptimizer.core import consts

UID = NewType("UID", str)
Version = NewType("Version", int)
Component = NewType("Component", str)


def get_component_name(component: Any) -> Component:
    if isinstance(component, type):
        return Component(component.__name__)

    if isinstance(component, types.MethodType):
        return Component(f"{component.__self__.__class__.__name__}.{component.__func__.__name__}")

    return Component(component.__class__.__name__)


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
AccName = NewType("AccName", str)


@unique
class Currency(StrEnum):
    RUR = auto()
    USD = auto()


class Event(BaseModel): ...


class Entity(BaseModel):
    rev: Revision
    day: Day

    @property
    def uid(self) -> UID:
        return self.rev.uid

    @property
    def ver(self) -> Version:
        return self.rev.ver


class Row(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class _RowWithDate(Protocol):
    day: Day


def sorted_by_day_validator(df: list[_RowWithDate]) -> list[_RowWithDate]:
    dates_pairs = itertools.pairwise(row.day for row in df)

    if not all(day < next_ for day, next_ in dates_pairs):
        raise ValueError("df not sorted by day")

    return df


def after_start_date_validator(df: list[_RowWithDate]) -> list[_RowWithDate]:
    if df and (day := df[0].day) < consts.START_DAY:
        raise ValueError(f"day before start day {day}")

    return df
