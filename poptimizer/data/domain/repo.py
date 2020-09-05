"""Реализация репозиторий с таблицами."""
import asyncio
from datetime import datetime
from types import TracebackType
from typing import AsyncContextManager, Dict, NamedTuple, Optional, Type

from poptimizer.data.domain import factories, model
from poptimizer.data.ports import base, outer


class TimedTable(NamedTuple):
    """Таблица и момент времени на момент загрузки или создания."""

    table: model.Table
    timestamp: Optional[datetime]


class Repo(AsyncContextManager[None]):
    """Класс репозитория для хранения таблиц.

    Контекстный менеджер обеспечивающий блокировку для проведения атомарных операций по добавлению и
    извлечению таблиц.
    """

    def __init__(self, db_session: outer.AbstractDBSession) -> None:
        """Сохраняются ссылки на таблицы, которые были добавлены или взяты из репозитория."""
        self._session = db_session
        self._seen: Dict[base.TableName, TimedTable] = {}
        self._seen_loc = asyncio.Lock()

    async def __aenter__(self) -> None:
        """Возвращает репо с таблицами."""
        await self._seen_loc.acquire()

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Сохраняет изменные данные в базу данных."""
        self._seen_loc.release()

    def add_table(self, table: model.Table) -> None:
        """Добавляет таблицу в репозиторий."""
        self._seen[table.name] = TimedTable(table, None)

    async def get_table(self, table_name: base.TableName) -> Optional[model.Table]:
        """Берет таблицу из репозитория."""
        if (timed_table := self._seen.get(table_name)) is not None:
            return timed_table.table

        if (table_tuple := await self._session.get(table_name)) is None:
            return None

        table = factories.recreate_table(table_tuple)
        self._seen[table.name] = TimedTable(table, table.timestamp)

        return table

    async def commit(self) -> None:
        """Сохраняет изменения в базу данных."""
        async with self._seen_loc:
            for_commit = (
                factories.convent_to_tuple(table)
                for table, timestamp in self._seen.values()
                if timestamp != table.timestamp
            )
            await self._session.commit(for_commit)
