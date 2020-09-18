"""Группа операций с таблицами, в конце которой осуществляется сохранение изменных данных."""
import asyncio
import contextlib
import types
from typing import AsyncIterator, Awaitable, Dict, Final, List

import pandas as pd

from poptimizer.data.domain import events, repo, services
from poptimizer.data.ports import outer

EVENT_HANDLERS: Final = types.MappingProxyType(
    {
        events.UpdatedDfRequired: services.select_update_type,
        events.UpdateWithHelperRequired: services.update_with_helper,
        events.UpdateWithTimestampRequired: services.update_with_timestamp,
    },
)


@contextlib.asynccontextmanager
async def unit_of_work(
    db_session: outer.AbstractDBSession,
) -> AsyncIterator[repo.Repo]:
    """Одна транзакция в базу данных.

    Контекстный менеджер, возвращающий Репо для транзакций.
    """
    store = repo.Repo(db_session)
    try:
        yield store
    finally:
        await store.commit()


async def _create_task(coro: Awaitable[None], events_queue: events.EventsQueue) -> None:
    task = asyncio.create_task(coro)
    task.add_done_callback(lambda _: events_queue.task_done())


async def _queue_processor(
    events_queue: events.EventsQueue,
    store: repo.Repo,
) -> Dict[outer.TableName, pd.DataFrame]:
    """Вытягивает сообщения из очереди событий и запускает их обработку."""
    events_results: Dict[outer.TableName, pd.DataFrame] = {}
    n_results = events_queue.qsize()
    while len(events_results) < n_results:

        event = await events_queue.get()
        if (event_handler := EVENT_HANDLERS.get(type(event))) is not None:
            coro = event_handler(events_queue, store, event)
            await _create_task(coro, events_queue)
            continue

        if isinstance(event, events.Result):
            events_results[event.table_name] = event.df
            events_queue.task_done()
            continue

        raise outer.DataError("Неизвестный тип события")

    return events_results


class EventsBus:
    """Шина для обработки сообщений."""

    def __init__(self, db_session: outer.AbstractDBSession) -> None:
        """Сохраняет параметры для создания изолированных UoW."""
        self._db_session = db_session

    async def handle_events(
        self,
        events_list: List[events.AbstractEvent],
    ) -> Dict[outer.TableName, pd.DataFrame]:
        """Обработка сообщения и следующих за ним."""
        events_queue: events.EventsQueue = asyncio.Queue()
        for event in events_list:
            await events_queue.put(event)

        async with unit_of_work(self._db_session) as store:
            processor_task = asyncio.create_task(_queue_processor(events_queue, store))
            await events_queue.join()
        return processor_task.result()
