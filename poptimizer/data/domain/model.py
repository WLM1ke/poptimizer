"""Основные классы модели данных - таблица и реестр таблиц."""
from datetime import datetime
from typing import Optional

import pandas as pd

from poptimizer.data import ports


class Table:
    """Класс таблицы с данными."""

    def __init__(
        self,
        name: ports.TableName,
        helper_table: Optional["Table"] = None,
        df: Optional[pd.DataFrame] = None,
        timestamp: Optional[datetime] = None,
    ):
        """Имеет имя и данные, а так же автоматически сохраняет момент обновления UTC.

        Может иметь вспомогательную таблицу, необходимую для обновления основной.

        :param name:
            Наименование таблицы.
        :param helper_table:
            Вспомогательная таблица.
        :param df:
            Таблица.
        :param timestamp:
            Момент последнего обновления.
        """
        self._name = name
        self._helper_table = helper_table
        self._df = df
        self._timestamp = timestamp

    def __str__(self) -> str:
        """Отображает название класса и таблицы."""
        return f"{self.__class__.__name__}({', '.join(self._name)})"

    @property
    def name(self) -> ports.TableName:
        """Наименование таблицы."""
        return self._name

    @property
    def helper_table(self) -> Optional["Table"]:
        """Вспомогательная таблица."""
        return self._helper_table

    @property
    def df(self) -> Optional[pd.DataFrame]:
        """Таблица с данными."""
        if (df := self._df) is None:
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
