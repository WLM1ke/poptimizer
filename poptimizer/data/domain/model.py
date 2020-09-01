"""Основные классы модели данных - таблица и реестр таблиц."""
from datetime import datetime
from typing import Optional

import pandas as pd

from poptimizer.data.ports import app, base, outer


class Table:
    """Класс таблицы с данными."""

    def __init__(
        self,
        name: base.TableName,
        desc: app.TableDescription,
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

    def need_update(self, end_of_trading_day: datetime) -> bool:
        """Нужно ли обновить таблицу."""
        if self._timestamp is None:
            return True
        if end_of_trading_day > self._timestamp:
            return True
        return False

    def update(self) -> None:
        """Осуществляет необходимые проверки и обновляет таблицу."""
        loader = self._loader
        df_old = self.df
        name = self._name

        if df_old is None:
            self._set_df(loader(name))
            return

        if isinstance(loader, outer.AbstractLoader):
            df_new = loader(name)
        else:
            date = df_old.index[-1].date()
            df_new = loader(name, date)
            df_new = pd.concat([df_old.iloc[:-1], df_new], axis=0)

        if self._validate:
            df_new = df_new.reindex(df_old.index)
            try:
                pd.testing.assert_frame_equal(df_new, df_old)
            except AssertionError:
                raise base.DataError("Новые данные не соответствуют старым")

        self._set_df(df_new)

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
