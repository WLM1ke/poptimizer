"""Группа операций с таблицами, в конце которой осуществляется сохранение изменных данных."""
from typing import Callable

import pandas as pd

from poptimizer.data.domain import factories, model, repo
from poptimizer.data.ports import base, outer


def _load_or_create_table(
    table_name: base.TableName,
    store: repo.Repo,
) -> model.Table:
    if (table := store.get_table(table_name)) is None:
        table = factories.create_table(table_name)
        store.add_table(table)
    return table


class EventsBus(outer.AbstractEventsBus):
    """Шина для обработки сообщений."""

    def __init__(self, repo_factory: Callable[[], repo.Repo]) -> None:
        """Сохраняет параметры для создания изолированных репо для каждой обработки события."""
        self._repo_factory = repo_factory

    def handle_event(self, message: outer.AbstractEvent) -> None:
        """Обработка сообщения и следующих за ним."""
        messages = [message]
        repo_factory = self._repo_factory
        while messages:
            message = messages.pop()
            with repo_factory() as store:
                tables_dict = {
                    table_name: _load_or_create_table(table_name, store)
                    for table_name in message.tables_required
                }
                message.handle_event(tables_dict)
            messages.extend(message.new_events)


class Viewer(outer.AbstractViewer):
    """Позволяет смотреть DataFrame по имени таблицы."""

    def __init__(self, repo_factory: Callable[[], repo.Repo]) -> None:
        """Сохраняет репо для просмотра данных."""
        self._repo = repo_factory()

    def get_df(self, table_name: base.TableName) -> pd.DataFrame:
        """Возвращает DataFrame по имени таблицы."""
        with self._repo as store:
            if (table := store.get_table(table_name)) is None:
                raise base.DataError(f"Таблицы {table_name} нет в хранилище")
            return table.df
