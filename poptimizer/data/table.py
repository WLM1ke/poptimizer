"""Базовый класс таблицы с данными и типа данных."""
from datetime import datetime
from typing import Optional

import pandas as pd

from poptimizer.data.registry import TableName


class Table:
    """Базовый класс таблицы с данными."""

    def __init__(self, name: TableName, df: pd.DataFrame, timestamp: Optional[datetime] = None):
        """При создании и последующем обновлении автоматически сохраняется момент UTC.

        :param name:
            Наименование, если тип имеет множество таблиц.
        :param df:
            Таблица.
        :param timestamp:
            Момент последнего обновления.
        """
        self._name = name
        self._df = df
        self._timestamp = timestamp or datetime.utcnow()

    def __str__(self) -> str:
        """Отображает название класса и таблицы."""
        return f"{self.__class__.__name__}({', '.join(self._name)})"

    @property
    def df(self) -> pd.DataFrame:
        """Таблица с данными."""
        return self._df.copy()

    @df.setter
    def df(self, df: pd.DataFrame) -> None:
        """Устанавливает новое значение и обновляет момент обновления UTC."""
        self._df = df

    @property
    def timestamp(self) -> datetime:
        """Момент обновления данных UTC."""
        return self._timestamp

    @property
    def name(self) -> TableName:
        """Наименование таблицы."""
        return self._name
