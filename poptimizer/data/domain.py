"""Описание доменных объектов."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique

import pandas as pd

from poptimizer import config


@unique
class Columns(str, Enum):  # noqa: WPS600
    """Наименования столбцов в таблицах."""

    DATE = "DATE"
    VALUE = "VALUE"  # noqa: WPS110
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    HIGH = "HIGH"
    LOW = "LOW"
    TURNOVER = "TURNOVER"

    def __str__(self) -> str:
        """Отображается в виде названия, а не стандартного описания."""
        return self.name


@unique
class Group(Enum):
    """Группы таблиц."""

    TRADING_DATE = "trading_date"
    CPI = "cpi"
    INDEXES = "indexes"


@dataclass(slots=True, frozen=True, kw_only=True)
class Table:
    """Таблица с рыночными данными.

    Таблицы разбиты на группы, некоторые из которых содержат единственный элемент. В таком случае название элемента
    не указывается.
    """

    group: Group
    name: str | None = None
    timestamp: datetime | None = None
    df: pd.DataFrame | None = None

    def new_revision(self, timestamp: datetime, df: pd.DataFrame) -> Table:
        """Создает новую версию таблицы."""
        return Table(
            group=self.group,
            name=self.name,
            timestamp=timestamp,
            df=df,
        )


class DataError(config.POError):
    """Ошибки, связанные с операциями над данными."""


def raise_not_unique_increasing_index(df: pd.DataFrame) -> None:
    """Тестирует индекс на уникальность и возрастание."""
    index = df.index

    if not index.is_monotonic_increasing:
        raise DataError("index is not increasing")

    if not index.is_unique:
        raise DataError("index is not unique")


def raise_dfs_mismatch(df: pd.DataFrame, df_old: pd.DataFrame) -> None:
    """Сравнивает новые данные со старыми для старого индекса."""
    if df_old is None:
        return

    df_new_val = df.reindex(df_old.index)
    try:
        pd.testing.assert_frame_equal(df_new_val, df_old, check_dtype=False)
    except AssertionError as err:
        raise DataError("dfs mismatch") from err
