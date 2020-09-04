"""Запросы таблиц."""
from typing import Callable, List

import pandas as pd

from poptimizer.data.app import services
from poptimizer.data.domain import events
from poptimizer.data.domain.repo import Repo
from poptimizer.data.ports import base, outer


class Handler:
    """Обработчик запросов к приложению."""

    def __init__(self, repo_factory: Callable[[], Repo]):
        """Создает шину сообщений и просмотрщик данных."""
        self._bus = services.EventsBus(repo_factory)
        self._viewer = services.Viewer(repo_factory)

    def get_df(
        self,
        table_name: base.TableName,
        force_update: bool = False,
    ) -> pd.DataFrame:
        """Возвращает DataFrame по наименованию таблицы."""
        event = events.UpdateDataFrame(table_name, force_update)
        self._bus.handle_events([event])
        return self._viewer.get_df(table_name)

    def get_dfs(self, group: base.GroupName, names: List[str]) -> List[pd.DataFrame]:
        """Возвращает несколько DataFrame из одной группы."""
        table_names = [base.TableName(group, name) for name in names]

        update_events: List[outer.AbstractEvent] = [
            events.UpdateDataFrame(table_name) for table_name in table_names
        ]
        self._bus.handle_events(update_events)

        return [self._viewer.get_df(table_name) for table_name in table_names]
