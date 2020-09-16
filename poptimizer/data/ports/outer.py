"""Интерфейсы служб и вспомогательных типов данных."""
import abc
import datetime
from typing import Iterable, List, NamedTuple, Optional

import pandas as pd

from poptimizer.data.domain import events
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


class AbstractEventsBus(abc.ABC):
    """Шина для обработки сообщений."""

    @abc.abstractmethod
    async def handle_events(self, events_list: List[events.AbstractEvent]) -> None:
        """Обработка сообщения и следующих за ним."""


class AbstractViewer(abc.ABC):
    """Позволяет смотреть DataFrame по имени таблицы."""

    @abc.abstractmethod
    async def get_df(self, table_name: base.TableName) -> pd.DataFrame:
        """Возвращает DataFrame по имени таблицы."""
