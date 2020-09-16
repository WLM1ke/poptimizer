"""Интерфейсы служб и вспомогательных типов данных."""
import abc
import datetime
from typing import Iterable, NamedTuple, Optional

import pandas as pd

from poptimizer.data.ports import base


class TableTuple(NamedTuple):
    """Представление таблицы в виде кортежа."""

    group: base.GroupName
    name: str
    df: pd.DataFrame
    timestamp: datetime.datetime


class AbstractDBSession(abc.ABC):
    """Сессия работы с базой данных."""

    @abc.abstractmethod
    async def get(self, table_name: base.TableName) -> Optional[TableTuple]:
        """Получает данные из хранилища."""

    @abc.abstractmethod
    async def commit(self, tables_vars: Iterable[TableTuple]) -> None:
        """Сохраняет данные таблиц."""
