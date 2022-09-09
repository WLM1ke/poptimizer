"""Описание доменных объектов."""
import itertools
from datetime import datetime
from enum import Enum, unique
from typing import ClassVar, Generic, Protocol, TypeVar

from pydantic import BaseModel, Field, validator
from pydantic.generics import GenericModel


@unique
class Group(str, Enum):  # noqa: WPS600
    """Группы таблиц."""

    TRADING_DATE = "trading_date"
    CPI = "cpi"
    INDEXES = "indexes"
    SECURITIES = "securities"
    STATUS = "status"

    def __str__(self) -> str:
        """Отображение в виде значения."""
        return self.value


class Row(BaseModel):
    """Строка с данными."""

    @validator("date", pre=True, check_fields=False)
    def _string_date_to_datetime(cls, date: str | datetime) -> datetime:
        if isinstance(date, str):
            date = datetime.fromisoformat(date)

        if date != datetime(*date.timetuple()[:3]):
            raise ValueError(f"not a date {date}")

        return date

    class Config:
        """Загрузка объектов по псевдонимам и названиям полей."""

        allow_population_by_field_name = True


_RowT = TypeVar("_RowT")


class Payload(GenericModel, Generic[_RowT]):
    """Строки с данными загруженные из внешних источников."""

    df: list[_RowT]


class Table(BaseModel):
    """Таблица с данными."""

    group: ClassVar[Group]
    id_: str = Field(alias="_id", exclude=True)
    timestamp: datetime = datetime.fromtimestamp(0)

    class Config:
        """Загрузка объектов по псевдонимам и названиям полей."""

        allow_population_by_field_name = True


class _RowWithDate(Protocol):
    date: datetime


def validate_sorted_by_date(df: list[_RowWithDate]) -> list[_RowWithDate]:
    """Валидирует сортировку списка по полю даты по возрастанию."""
    dates_pairs = itertools.pairwise(row.date for row in df)

    if not all(date < next_ for date, next_ in dates_pairs):
        raise ValueError("dates are not sorted")

    return df
