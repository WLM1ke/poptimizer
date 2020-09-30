"""Запросы таблиц."""
import asyncio
from typing import Dict, List, Tuple

import pandas as pd

from poptimizer.data.app import event_bus
from poptimizer.data.domain import events
from poptimizer.data.ports import outer


class Handler:
    """Обработчик запросов к приложению."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        db_session: outer.AbstractDBSession,
    ):
        """Создает шину сообщений и просмотрщик данных."""
        self._loop = loop
        self._bus = event_bus.EventBus(db_session)

    def get_df(
        self,
        table_name: outer.TableName,
        force_update: bool = False,
    ) -> pd.DataFrame:
        """Возвращает DataFrame по наименованию таблицы."""
        command = events.GetDataFrame(table_name, force_update)
        result_dict = self._run_commands([command])
        return result_dict[table_name]

    def get_dfs(
        self,
        group: outer.GroupName,
        names: Tuple[str, ...],
    ) -> Tuple[pd.DataFrame, ...]:
        """Возвращает несколько DataFrame из одной группы."""
        table_names = [outer.TableName(group, name) for name in names]

        commands: List[events.Command] = [events.GetDataFrame(table_name) for table_name in table_names]
        result_dict = self._run_commands(commands)
        return tuple(result_dict[name] for name in table_names)

    def _run_commands(self, commands: List[events.Command]) -> Dict[outer.TableName, pd.DataFrame]:
        return self._loop.run_until_complete(self._bus.handle_events(commands))
