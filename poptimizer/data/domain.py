"""Описание доменных объектов."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique

import pandas as pd


@unique
class Columns(str, Enum):  # noqa: WPS600
    """Наименования столбцов в таблицах."""

    DATE = "DATE"

    def __str__(self) -> str:
        """Отображается в виде названия, а не стандартного описания."""
        return self.name


@unique
class Group(Enum):
    """Группы таблиц."""

    TRADING_DATE = "trading_date"


@dataclass(slots=True, frozen=True, kw_only=True)
class Table:
    """Таблица с рыночными данными."""

    group: Group
    name: str | None
    timestamp: datetime | None
    df: pd.DataFrame | None
