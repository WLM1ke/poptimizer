"""Основные классы модели данных - таблица и реестр таблиц."""
import asyncio
from datetime import datetime
from typing import Optional

import pandas as pd

from poptimizer.data.ports import base


class Table:
    """Класс таблицы с данными."""

    def __init__(
        self,
        name: base.TableName,
        desc: base.TableDescription,
        df: Optional[pd.DataFrame] = None,
        timestamp: Optional[datetime] = None,
    ):
        """Имеет имя и данные, а так же автоматически сохраняет момент обновления UTC.

        Может иметь вспомогательную таблицу, необходимую для обновления основной.

        :param name:
            Наименование таблицы.
        :param desc:
            Описание правил обновления таблицы.
        :param df:
            Таблица.
        :param timestamp:
            Момент последнего обновления.
        """
        self._name = name
        self._loader = desc.loader
        self._index_checks = desc.index_checks
        self._validate = desc.validate
        self._df = df
        self._timestamp = timestamp
        self._df_lock = asyncio.Lock()

    @property
    def name(self) -> base.TableName:
        """Наименование таблицы."""
        return self._name

    @property
    def df(self) -> Optional[pd.DataFrame]:
        """Таблица с данными."""
        if (df := self._df) is None:
            return None
        return df.copy()

    @property
    def timestamp(self) -> Optional[datetime]:
        """Момент последнего обновления таблицы."""
        return self._timestamp

    async def update(self, end_of_trading_day: Optional[datetime]) -> None:
        """Обновляет таблицу.

        Если конец рабочего дня None, то принудительно. В ином случае, если данные устарели.
        """
        async with self._df_lock:
            timestamp = self._timestamp
            if (end_of_trading_day is None) or (timestamp is None) or end_of_trading_day > timestamp:
                df_new = await self._prepare_df()
                self._validate_df(df_new)
                self._timestamp = datetime.utcnow()
                self._df = df_new

    async def _prepare_df(self) -> pd.DataFrame:
        """Готовит новый DataFrame и осуществляет необходимые проверки."""
        loader = self._loader
        df_old = self.df
        name = self._name

        if df_old is None:
            return await loader.get(name)

        if isinstance(loader, base.AbstractLoader):
            return await loader.get(name)

        date = df_old.index[-1].date()
        df_new = await loader.get(name, date)
        return pd.concat([df_old.iloc[:-1], df_new], axis=0)

    def _validate_df(self, df_new: pd.DataFrame) -> None:
        """Проверяет значения и индекс новых данных."""
        df_old = self._df

        if df_old is not None and self._validate:
            df_new_val = df_new.reindex(df_old.index)
            try:
                pd.testing.assert_frame_equal(df_new_val, df_old)
            except AssertionError:
                raise base.DataError("Новые данные не соответствуют старым")

        index = df_new.index
        index_checks = self._index_checks
        if index_checks & base.IndexChecks.UNIQUE and not index.is_unique:
            raise base.DataError(f"Индекс не уникален\n{df_new}")
        if index_checks & base.IndexChecks.ASCENDING and not index.is_monotonic_increasing:
            raise base.DataError(f"Индекс не возрастает\n{df_new}")
