"""Группа операций с таблицами, в конце которой осуществляется сохранение изменных данных."""
import asyncio
import contextlib
from typing import TYPE_CHECKING, AsyncIterator, List, Tuple

import pandas as pd

from poptimizer.data.domain import factories, model, repo
from poptimizer.data.ports import base, outer

if TYPE_CHECKING:
    EventsQueue = asyncio.Queue[outer.AbstractEvent]
else:
    EventsQueue = asyncio.Queue


@contextlib.asynccontextmanager
async def unit_of_work(db_session: outer.AbstractDBSession) -> AsyncIterator[repo.Repo]:
    """Одна транзакция в базу данных.

    Контекстный менеджер, возвращающий Репо для транзакций.
    """
    store = repo.Repo(db_session)
    try:
        yield store
    finally:
        await store.commit()


async def _load_or_create_table(
    table_name: base.TableName,
    store: repo.Repo,
) -> Tuple[base.TableName, model.Table]:
    async with store:
        if (table := await store.get_table(table_name)) is None:
            table = factories.create_table(table_name)
            store.add_table(table)
        return table_name, table


async def _put_in_queue(events: List[outer.AbstractEvent], events_queue: EventsQueue) -> None:
    for event in events:
        await events_queue.put(event)


async def _handle_one_event(
    event: outer.AbstractEvent,
    store: repo.Repo,
    queue: EventsQueue,
) -> None:
    """Обрабатывает одно событие и возвращает  дочерние."""
    aws = [_load_or_create_table(table_name, store) for table_name in event.tables_required]
    tables_dict = dict(await asyncio.gather(*aws))
    event.handle_event(tables_dict)
    await _put_in_queue(event.new_events, queue)
    queue.task_done()


class EventsBus(outer.AbstractEventsBus):
    """Шина для обработки сообщений."""

    def __init__(self, db_session: outer.AbstractDBSession) -> None:
        """Сохраняет параметры для создания изолированных UoW."""
        self._db_session = db_session

    async def handle_events(self, events: List[outer.AbstractEvent]) -> None:
        """Обработка сообщения и следующих за ним."""
        events_queue: EventsQueue = asyncio.Queue()
        await _put_in_queue(events, events_queue)

        async with unit_of_work(self._db_session) as store:
            while not events_queue.empty():
                event = await events_queue.get()
                asyncio.create_task(_handle_one_event(event, store, events_queue))


class Viewer(outer.AbstractViewer):
    """Позволяет смотреть DataFrame по имени таблицы."""

    def __init__(self, db_session: outer.AbstractDBSession) -> None:
        """Сохраняет репо для просмотра данных."""
        self._db_session = db_session

    async def get_df(self, table_name: base.TableName) -> pd.DataFrame:
        """Возвращает DataFrame по имени таблицы."""
        if (table_tuple := await self._db_session.get(table_name)) is None:
            raise base.DataError(f"Таблицы {table_name} нет в хранилище")
        table = factories.recreate_table(table_tuple)
        return table.df
