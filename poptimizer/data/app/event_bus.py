"""Шина событий по обновлению таблиц и получению из них данных."""
import asyncio
from asyncio import Future
from typing import Dict, List, Set

import pandas as pd

from poptimizer.data.domain import events, repo
from poptimizer.data.ports import outer

PendingTasks = Set[Future[events.AbstractEvent]]


async def _handle_one_command(
    db_session: outer.AbstractDBSession,
    event: events.Command,
) -> events.AbstractEvent:
    """Обрабатывает одно событие и помечает его сделанным."""
    async with repo.Repo(db_session) as store:
        table = None
        if (table_name := event.table_required) is not None:
            table = await store.get_table(table_name)
        return await event.handle_event(table)


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
        pending: PendingTasks = {self._create_task(event) for event in events_list}
        events_results: Dict[outer.TableName, pd.DataFrame] = {}
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                event = task.result()
                if isinstance(event, events.Command):
                    pending.add(self._create_task(event))
                elif isinstance(event, events.Result):
                    events_results[event.name] = event.df

        return events_results

    def _create_task(self, event: events.Command) -> asyncio.Future[events.AbstractEvent]:
        """Создает задание для команды."""
        return asyncio.create_task(_handle_one_command(self._db_session, event))
