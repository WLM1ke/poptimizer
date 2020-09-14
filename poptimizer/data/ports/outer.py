"""Интерфейсы служб и вспомогательных типов данных."""
import abc
import asyncio
import datetime
from typing import TYPE_CHECKING, Iterable, List, NamedTuple, Optional

import pandas as pd

from poptimizer.data.domain import model
from poptimizer.data.ports import base

if TYPE_CHECKING:
    EventsQueue = asyncio.Queue["AbstractEvent"]
else:
    EventsQueue = asyncio.Queue


class AbstractEvent(abc.ABC):
    """Абстрактный класс события."""

    @property
    @abc.abstractmethod
    def table_required(self) -> Optional[base.TableName]:
        """Перечень таблиц, которые нужны обработчику события."""

    @abc.abstractmethod
    async def handle_event(
        self,
        queue: EventsQueue,
        table: Optional[model.Table],
    ) -> None:
        """Обрабатывает событие и добавляет новые события в очередь."""


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
    async def handle_events(self, events: List[AbstractEvent]) -> None:
        """Обработка сообщения и следующих за ним."""


class AbstractViewer(abc.ABC):
    """Позволяет смотреть DataFrame по имени таблицы."""

    @abc.abstractmethod
    async def get_df(self, table_name: base.TableName) -> pd.DataFrame:
        """Возвращает DataFrame по имени таблицы."""
