"""Шина событий по обновлению таблиц и получению из них данных."""
import asyncio
from typing import TYPE_CHECKING, Dict, List, Set

import pandas as pd

from poptimizer.data.domain import events, repo
from poptimizer.data.ports import outer

if TYPE_CHECKING:
    FutureEvent = asyncio.Future[events.AbstractEvent]
else:
    FutureEvent = asyncio.Future
PendingTasks = Set[FutureEvent]
ResultsDict = Dict[outer.TableName, pd.DataFrame]


def _gather_results(events_results: ResultsDict, event: events.AbstractEvent) -> None:
    """Добавляет результаты."""
    if isinstance(event, events.Result):
        events_results[event.name] = event.df


class EventBus:
    """Шина для обработки сообщений."""

    def __init__(self, db_session: outer.AbstractDBSession) -> None:
        """Сохраняет параметры для создания репо."""
        self._db_session = db_session

    async def handle_events(
        self,
        events_list: List[events.Command],
    ) -> ResultsDict:
        """Обработка сообщения и следующих за ним."""
        pending: PendingTasks = {self._create_task(event) for event in events_list}
        events_results: ResultsDict = {}
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                event = task.result()
                self._add_pending(pending, event)
                _gather_results(events_results, event)

        return events_results

    def _add_pending(self, pending: PendingTasks, event: events.AbstractEvent) -> None:
        """Добавляет новые задания по обработке событий."""
        if isinstance(event, events.Command):
            pending.add(self._create_task(event))

    async def _handle_one_command(self, event: events.Command) -> events.AbstractEvent:
        """Обрабатывает одно событие и помечает его сделанным."""
        async with repo.Repo(self._db_session) as store:
            table = None
            if (table_name := event.table_required) is not None:
                table = await store.get_table(table_name)
            return await event.handle_event(table)

    def _create_task(self, event: events.Command) -> FutureEvent:
        """Создает задание для команды."""
        return asyncio.create_task(self._handle_one_command(event))
