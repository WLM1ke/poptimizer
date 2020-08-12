"""Базовый класс таблицы с данными и типа данных."""
from datetime import datetime
from typing import NamedTuple, Optional

import pandas as pd


class TableKind(NamedTuple):
    """Описание разновидности таблицы с данными, особенностей обновления и валидации.

    - множество таблиц данного типа
    - обновляемая таблица или создается с нуля
    - уникальный индекс
    - возрастающий индекс
    """

    multiple: bool
    updatable: bool
    unique_index: bool
    ascending_index: bool


class Table:
    """Базовый класс таблицы с данными."""

    def __init__(self, df: pd.DataFrame, timestamp: datetime, kind: TableKind, name: Optional[str]):
        """При создании и последующем обновлении автоматически сохраняется момент UTC.

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

    @property
    def df(self) -> pd.DataFrame:
        """Таблица с данными."""
        return self._df.copy()

    @df.setter
    def df(self, df: pd.DataFrame) -> None:
        """Обновление таблицы с данными."""
        self._df = df
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
