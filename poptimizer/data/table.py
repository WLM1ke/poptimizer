"""Базовый класс таблицы с данными и типа данных."""
from datetime import datetime
from typing import Optional

import pandas as pd

from poptimizer.config import POptimizerError
from poptimizer.data.registry import TableName, get_specs


class TableError(POptimizerError):
    """Ошибки связанные с созданием и обновлением таблиц."""


class Table:
    """Базовый класс таблицы с данными."""

    def __init__(
        self, name: TableName, df: Optional[pd.DataFrame] = None, timestamp: Optional[datetime] = None,
    ):
        """При создании и последующем обновлении автоматически сохраняется момент UTC.

        Осуществляется проверка, что имя есть в реестре таблиц.

        :param name:
            Наименование, если тип имеет множество таблиц.
        :param df:
            Таблица.
        :param timestamp:
            Момент последнего обновления.
        :raises TableError:
            Имя отсутствует в реестре.
        """
        try:
            get_specs(name)
        except KeyError:
            raise TableError(f"Имя отсутствует в реестре - {name}")
        self._name = name
        self._df = df
        self._timestamp = timestamp

    def __str__(self) -> str:
        """Отображает название класса и таблицы."""
        return f"{self.__class__.__name__}({', '.join(self._name)})"

    @property
    def df(self) -> Optional[pd.DataFrame]:
        """Таблица с данными."""
        df = self._df
        if df is None:
            return None
        return df.copy()

    @df.setter
    def df(self, df: pd.DataFrame) -> None:
        """Устанавливает новое значение и обновляет момент обновления UTC."""
        self._timestamp = datetime.utcnow()
        self._df = df

    @property
    def timestamp(self) -> Optional[datetime]:
        """Момент обновления данных UTC."""
        return self._timestamp

    @property
    def name(self) -> TableName:
        """Наименование таблицы."""
        return self._name
