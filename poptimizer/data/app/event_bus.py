"""Шина событий по обновлению таблиц и получению из них данных."""
import asyncio
from typing import Dict, List, Optional, Tuple

import pandas as pd

from poptimizer.data.domain import events, repo
from poptimizer.data.ports import outer


async def _handle_one_command(
    db_session: outer.AbstractDBSession,
    queue: events.EventsQueue,
    event: events.Command,
) -> None:
    """Обрабатывает одно событие и помечает его сделанным."""
    async with repo.Repo(db_session) as store:
        table = None
        if (table_name := event.table_required) is not None:
            table = await store.get_table(table_name)
        await event.handle_event(queue, table)
        queue.task_done()


async def _dispatch_event(
    db_session: outer.AbstractDBSession,
    events_queue: events.EventsQueue,
) -> Optional[Tuple[outer.TableName, pd.DataFrame]]:
    """Выбирает способ обработки события."""
    event = await events_queue.get()
    named_df = None
    if isinstance(event, events.Result):
        events_queue.task_done()
        named_df = (event.name, event.df)
    elif isinstance(event, events.Command):
        asyncio.create_task(_handle_one_command(db_session, events_queue, event))
    else:
        raise outer.DataError("Неизвестный тип события")

    return named_df


async def _queue_processor(
    db_session: outer.AbstractDBSession,
    events_queue: events.EventsQueue,
) -> Dict[outer.TableName, pd.DataFrame]:
    """Вытягивает сообщения из очереди событий, запускает их обработку и собирает результаты."""
    events_results: Dict[outer.TableName, pd.DataFrame] = {}
    n_results = events_queue.qsize()
    while len(events_results) < n_results:
        maybe_rez = await _dispatch_event(db_session, events_queue)
        if maybe_rez is not None:
            table_name, df = maybe_rez
            events_results[table_name] = df
    return events_results


class EventBus:
    """Шина для обработки сообщений."""

    def __init__(self, db_session: outer.AbstractDBSession) -> None:
        """Сохраняет параметры для создания репо."""
        self._db_session = db_session

    async def handle_events(
        self,
        events_list: List[events.Command],
    ) -> Dict[outer.TableName, pd.DataFrame]:
        """Обработка сообщения и следующих за ним."""
        events_queue: events.EventsQueue = asyncio.Queue()
        for event in events_list:
            await events_queue.put(event)

        processor_task = asyncio.create_task(_queue_processor(self._db_session, events_queue))
        await events_queue.join()
        return processor_task.result()
