"""Базовый класс таблицы с данными."""
from datetime import datetime

import pandas as pd


class Table:
    """Базовый класс таблицы с данными."""

    def __init__(self, df: pd.DataFrame):
        """При создании и последующем обновлении автоматически сохраняется момент UTC.

        :param df:
            Таблица.
        """
        self._df = df
        self._timestamp = datetime.utcnow()

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
