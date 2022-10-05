"""Описание доменных объектов."""
from datetime import datetime
from enum import Enum, unique
from typing import ClassVar, Final, Generic, TypeVar

from pydantic import BaseModel, Field, validator
from pydantic.generics import GenericModel

_DATA_DB: Final = "data_new"
_PORTFOLIO_DB: Final = "portfolio"
_DL_DB: Final = "dl"


@unique
class Group(Enum):
    """Группы объектов.

    Объекты разбиты на отдельные модули (изолированные контексты), а в рамках модуля на группы.
    """

    TRADING_DATE = (_DATA_DB, "trading_date")
    CPI = (_DATA_DB, "cpi")
    INDEXES = (_DATA_DB, "indexes")
    SECURITIES = (_DATA_DB, "securities")
    USD = (_DATA_DB, "usd")
    QUOTES = (_DATA_DB, "quotes")
    DIVIDENDS = (_DATA_DB, "dividends")
    STATUS = (_DATA_DB, "status")
    RAW_DIV = (_DATA_DB, "raw_div")
    REESTRY = (_DATA_DB, "reestry")

    NASDAQ = (_DATA_DB, "nasdaq")
    PORTFOLIO = (_PORTFOLIO_DB, "portfolio")

    FEATURES = (_DL_DB, "features")

    def __str__(self) -> str:
        """Отображение в виде 'module.group'."""
        return ".".join(self.value)

    @property
    def module(self) -> str:
        """Модуль, к которому принадлежит объект."""
        return self.value[0]

    @property
    def group(self) -> str:
        """Группа в рамках модуля, к которому принадлежит объект."""
        return self.value[1]


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
            date = datetime.fromisoformat(date.removesuffix("Z"))
        if date != datetime(*date.timetuple()[:3]):
            raise ValueError(f"wrong {date}")
        return date

    class Config:
        """Загрузка объектов по псевдонимам и названиям полей."""

        allow_population_by_field_name = True


_RowT = TypeVar("_RowT")


class Rows(GenericModel, Generic[_RowT]):
    """Строки с данными загруженные из внешних источников."""

    __root__: list[_RowT]


class BaseEntity(BaseModel):
    """Базовый доменный объект."""

    group: ClassVar[Group]
    id_: str = Field(alias="_id", exclude=True)
    timestamp: datetime = datetime.fromtimestamp(0)

    class Config:
        """Загрузка объектов по псевдонимам и названиям полей."""

        allow_population_by_field_name = True
