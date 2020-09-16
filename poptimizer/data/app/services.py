"""Группа операций с таблицами, в конце которой осуществляется сохранение изменных данных."""
import asyncio
import contextlib
from typing import AsyncIterator, List

import pandas as pd

from poptimizer.data.domain import events, factories, model, repo
from poptimizer.data.ports import base, outer


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
) -> model.Table:
    async with store:
        if (table := await store.get_table(table_name)) is None:
            table = factories.create_table(table_name)
            store.add_table(table)
        return table


async def _handle_one_event(
    event: events.AbstractEvent,
    store: repo.Repo,
    queue: events.EventsQueue,
) -> None:
    """Обрабатывает одно событие и добавляет в очередь дочерние события."""
    table = None
    if (table_name := event.table_required) is not None:
        table = await _load_or_create_table(table_name, store)
    await event.handle_event(queue, table)
    queue.task_done()


async def _queue_processor(events_queue: events.EventsQueue, store: repo.Repo) -> None:
    """Вытягивает сообщения из очереди событий и запускает их обработку."""
    while True:
        event = await events_queue.get()
        asyncio.create_task(_handle_one_event(event, store, events_queue))


class EventsBus(outer.AbstractEventsBus):
    """Шина для обработки сообщений."""

    def __init__(self, db_session: outer.AbstractDBSession) -> None:
        """Сохраняет параметры для создания изолированных UoW."""
        self._db_session = db_session

    async def handle_events(self, events_list: List[events.AbstractEvent]) -> None:
        """Обработка сообщения и следующих за ним."""
        events_queue: events.EventsQueue = asyncio.Queue()
        for event in events_list:
            await events_queue.put(event)

        async with unit_of_work(self._db_session) as store:
            processor_task = asyncio.create_task(_queue_processor(events_queue, store))
            await events_queue.join()
            processor_task.cancel()


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
