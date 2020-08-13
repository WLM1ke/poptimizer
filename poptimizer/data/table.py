"""Базовый класс таблицы с данными и типа данных."""
from datetime import datetime
from typing import NamedTuple, Optional

import pandas as pd

from poptimizer.config import POptimizerError


class DataUpdateError(POptimizerError):
    """Ошибка при обновление данных."""


class TableKind(NamedTuple):
    """Описание разновидности таблицы с данными, особенностей обновления и валидации.

    - множество таблиц данного типа
    - обновляемая таблица или создается с нуля
    - уникальный индекс
    - возрастающий индекс
    """

    name: str
    multiple: bool
    updatable: bool
    unique_index: bool
    ascending_index: bool


class Table:
    """Базовый класс таблицы с данными."""

    def __init__(self, df: pd.DataFrame, timestamp: datetime, kind: TableKind, name: Optional[str]):
        """При последующем обновлении автоматически сохраняется момент UTC.

        :param df:
            Таблица.
        :param timestamp:
            Момент последнего обновления.
        :param kind:
            Тип таблицы.
        :param name:
            Наименование, если тип имеет множество таблиц.
        """
        self._df = df
        self._timestamp = timestamp
        self._kind = kind
        self._name = name

    def __str__(self) -> str:
        """Отображает название класса, имя типа данных и наименованием, если присутствует."""
        name = [self.kind.name]
        if self.name is not None:
            name.append(self.name)
        return f"{self.__class__.__name__}({', '.join(name)})"

    @property
    def df(self) -> pd.DataFrame:
        """Таблица с данными."""
        return self._df.copy()

    def update_table(self, df_update: pd.DataFrame) -> None:
        """Обновляет таблицу с помощью таблицы, содержащей обновление."""
        _validate_update(self, df_update)
        if self.kind.updatable:
            df_update = pd.concat([self.df, df_update.iloc[1:]], axis=0)
        _validate_index(self, df_update.index)
        self._df = df_update
        self._timestamp = datetime.utcnow()

    @property
    def timestamp(self) -> datetime:
        """Момент обновления данных UTC."""
        return self._timestamp

    @property
    def kind(self) -> TableKind:
        """Тип таблицы."""
        return self._kind

    @property
    def name(self) -> Optional[str]:
        """Наименование таблицы."""
        return self._name


def _validate_update(table: Table, df_update: pd.DataFrame) -> None:
    """Проверяет соответствие старых и новых данных."""
    df = table.df
    if table.kind.updatable:
        df = df.iloc[-1:]
        df_update = df_update.iloc[:1]
    else:
        df_update = df_update.iloc[: len(df)]

    try:
        pd.testing.assert_frame_equal(df, df_update)
    except AssertionError as error:
        raise DataUpdateError(f"{table}: новые данные не соответствуют старым", error)


def _validate_index(table: Table, index: pd.Index) -> None:  # type: ignore
    """Проверяет индекс в таблице с учетом настроек."""
    kind = table.kind
    if kind.unique_index and not index.is_unique:  # type: ignore
        raise DataUpdateError(f"{table}: индекс не уникальный")
    if kind.ascending_index and not index.is_monotonic_increasing:  # type: ignore
        raise POptimizerError(f"{table}: индекс не возрастает")
