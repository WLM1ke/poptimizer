"""Запросы таблиц."""
from typing import Callable

import pandas as pd

from poptimizer.data.app import services
from poptimizer.data.domain import events
from poptimizer.data.domain.repo import Repo
from poptimizer.data.ports import base


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
        """Возвращает таблицу по наименованию."""
        event = events.UpdateDataFrame(table_name, force_update)
        self._bus.handle_event(event)
        return self._viewer.get_df(table_name)
