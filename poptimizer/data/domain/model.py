"""Таблица с данными."""
import asyncio
import enum
from datetime import datetime
from typing import NamedTuple, Optional

import pandas as pd

from poptimizer.data.domain import entity
from poptimizer.data.ports import outer
from poptimizer.data.ports.outer import Loaders


class IndexChecks(enum.Flag):
    """Виды проверок для индекса таблицы."""

    NO_CHECKS = 0  # noqa: WPS115
    UNIQUE = enum.auto()  # noqa: WPS115
    ASCENDING = enum.auto()  # noqa: WPS115
    UNIQUE_ASCENDING = UNIQUE | ASCENDING  # noqa: WPS115


class TableDescription(NamedTuple):
    """Описание правил обновления таблицы."""

    loader: Loaders
    index_checks: IndexChecks
    validate: bool


def _update_cond(timestamp: Optional[datetime], end_of_trading_day: Optional[datetime]) -> bool:
    """Правило обновления данных."""
    if timestamp is None:
        return True
    if end_of_trading_day is None:
        return True
    if end_of_trading_day > timestamp:
        return True
    return False


async def _prepare_df(
    name: outer.TableName,
    df: Optional[pd.DataFrame],
    loader: outer.Loaders,
) -> pd.DataFrame:
    """Готовит новый DataFrame."""
    if df is None:
        return await loader.get(name)
    if df.empty:
        return await loader.get(name)
    if isinstance(loader, outer.AbstractLoader):
        return await loader.get(name)

    date = df.index[-1].date()
    df_new = await loader.get(name, str(date))
    return pd.concat([df.iloc[:-1], df_new], axis=0)


def _validate_data(validate: bool, df_old: pd.DataFrame, df_new: pd.DataFrame) -> None:
    """Проверка совпадения данных для старых значений индекса."""
    if not validate:
        return
    if df_old is None:
        return

    df_new_val = df_new.reindex(df_old.index)
    try:
        pd.testing.assert_frame_equal(df_new_val, df_old)
    except AssertionError:
        raise outer.DataError("Новые данные не соответствуют старым")


def _check_index(check: IndexChecks, index: pd.Index) -> None:
    """Проверка свойств индекса."""
    if check & IndexChecks.UNIQUE and not index.is_unique:
        raise outer.DataError("Индекс не уникален")
    if check & IndexChecks.ASCENDING and not index.is_monotonic_increasing:
        raise outer.DataError("Индекс не возрастает")


class Table(entity.BaseEntity):
    """Класс таблицы с данными."""

    def __init__(
        self,
        name: outer.TableName,
        desc: TableDescription,
        df: Optional[pd.DataFrame] = None,
        timestamp: Optional[datetime] = None,
    ):
        """Имеет имя и данные, а так же автоматически сохраняет момент обновления UTC.

        При первоначальном создании имеет пустое (None) значение и дату обновления.

        :param name:
            Наименование таблицы.
        :param desc:
            Описание правил обновления таблицы.
        :param df:
            Таблица.
        :param timestamp:
            Момент последнего обновления.
        """
        super().__init__()
        self._name = name
        self._loader = desc.loader
        self._index_checks = desc.index_checks
        self._validate = desc.validate
        self._df = df
        self._timestamp = timestamp
        self._df_lock = asyncio.Lock()

    @property
    def name(self) -> outer.TableName:
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
            if _update_cond(timestamp, end_of_trading_day):
                df_new = await _prepare_df(self._name, self.df, self._loader)

                _validate_data(self._validate, self._df, df_new)
                _check_index(self._index_checks, df_new.index)

                self._timestamp = datetime.utcnow()
                self._df = df_new
