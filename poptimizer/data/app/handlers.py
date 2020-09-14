"""Запросы таблиц."""
import asyncio
from typing import Awaitable, List, Tuple

import pandas as pd

from poptimizer.data.app import services
from poptimizer.data.domain import events
from poptimizer.data.ports import base, outer


class Handler:
    """Обработчик запросов к приложению."""

    def __init__(self, loop: asyncio.AbstractEventLoop, db_session: outer.AbstractDBSession):
        """Создает шину сообщений и просмотрщик данных."""
        self._loop = loop
        self._bus = services.EventsBus(db_session)
        self._viewer = services.Viewer(db_session)

    def get_df(
        self,
        table_name: base.TableName,
        force_update: bool = False,
    ) -> pd.DataFrame:
        """Возвращает DataFrame по наименованию таблицы."""
        event = events.UpdateChecked(table_name, force_update)
        loop = self._loop
        loop.run_until_complete(self._bus.handle_events([event]))
        return loop.run_until_complete(self._viewer.get_df(table_name))

    def get_dfs(
        self,
        group: base.GroupName,
        names: Tuple[str, ...],
    ) -> Tuple[pd.DataFrame, ...]:
        """Возвращает несколько DataFrame из одной группы."""
        table_names = [base.TableName(group, name) for name in names]

        update_events: List[outer.AbstractEvent] = [
            events.UpdateChecked(table_name) for table_name in table_names
        ]
        loop = self._loop
        loop.run_until_complete(self._bus.handle_events(update_events))

        aws = [self._viewer.get_df(table_name) for table_name in table_names]
        dfs: Awaitable[Tuple[pd.DataFrame, ...]] = asyncio.gather(*aws)
        return loop.run_until_complete(dfs)
