"""Описание доменных объектов."""
from datetime import datetime
from enum import Enum, unique
from typing import ClassVar, Generic, TypeVar

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
    RAW_DIV = "raw_div"
    REESTRY = "reestry"
    NASDAQ = "nasdaq"

    def __str__(self) -> str:
        """Отображение в виде значения."""
        return self.value


@unique
class Currency(str, Enum):  # noqa: WPS600
    """Валюты."""

    RUR = "RUR"
    USD = "USD"

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
