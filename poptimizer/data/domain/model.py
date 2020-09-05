"""Основные классы модели данных - таблица и реестр таблиц."""
import threading
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
        self._df_lock = threading.RLock()

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

    def update(self, end_of_trading_day: Optional[datetime]) -> None:
        """Обновляет таблицу.

        Если конец рабочего дня None, то принудительно. В ином случае, если данные устарели.
        """
        with self._df_lock:
            timestamp = self._timestamp
            if (end_of_trading_day is None) or (timestamp is None) or end_of_trading_day > timestamp:
                df = self._prepare_df()
                self._set_df(df)

    def _prepare_df(self) -> pd.DataFrame:
        """Готовит новый DataFrame и осуществляет необходимые проверки."""
        loader = self._loader
        df_old = self.df
        name = self._name

        if df_old is None:
            return loader(name)

        if isinstance(loader, base.AbstractLoader):
            df_new = loader(name)
        else:
            date = df_old.index[-1].date()
            df_new = loader(name, date)
            df_new = pd.concat([df_old.iloc[:-1], df_new], axis=0)

        if self._validate:
            df_new_val = df_new.reindex(df_old.index)
            try:
                pd.testing.assert_frame_equal(df_new_val, df_old)
            except AssertionError:
                raise base.DataError("Новые данные не соответствуют старым")

        return df_new

    def _set_df(self, df: pd.DataFrame) -> None:
        """Устанавливает новое значение и обновляет момент обновления UTC."""
        index = df.index
        index_checks = self._index_checks
        if index_checks & base.IndexChecks.UNIQUE and not index.is_unique:
            raise base.DataError(f"Индекс не уникален\n{df}")
        if index_checks & base.IndexChecks.ASCENDING and not index.is_monotonic_increasing:
            raise base.DataError(f"Индекс не возрастает\n{df}")

        self._timestamp = datetime.utcnow()
        self._df = df
