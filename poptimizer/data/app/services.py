"""Группа операций с таблицами, в конце которой осуществляется сохранение изменных данных."""
import functools
import itertools
from typing import Callable, List

import pandas as pd

from poptimizer.data.config import resources
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


def _handle_one_event(event: outer.AbstractEvent, store: repo.Repo) -> List[outer.AbstractEvent]:
    """Обрабатывает одно событие и возвращает  дочерние."""
    tables_dict = {
        table_name: _load_or_create_table(table_name, store) for table_name in event.tables_required
    }
    event.handle_event(tables_dict)
    return event.new_events


class EventsBus(outer.AbstractEventsBus):
    """Шина для обработки сообщений."""

    def __init__(self, repo_factory: Callable[[], repo.Repo]) -> None:
        """Сохраняет параметры для создания изолированных репо для каждой обработки события."""
        self._repo_factory = repo_factory

    def handle_event(self, event: outer.AbstractEvent) -> None:
        """Обработка сообщения и следующих за ним.

        Обработка сообщений идет поколениями - первое поколение генерирует поколение сообщений
        потомков и т.д. В рамках поколения обработка сообщений идет в несколько потоков с одной
        версией репо, что обеспечивает согласованность данных во всех потоках. После обработки
        поколения изменения сохраняются и создается новая версии репо для следующего поколения.
        """
        events = [event]
        thread_pool = resources.get_thread_pool()
        while events:
            with self._repo_factory() as store:
                one_event_handler = functools.partial(_handle_one_event, store=store)
                future_events = thread_pool.map(one_event_handler, events)
            events = list(itertools.chain.from_iterable(future_events))


class Viewer(outer.AbstractViewer):
    """Позволяет смотреть DataFrame по имени таблицы."""

    def __init__(self, repo_factory: Callable[[], repo.Repo]) -> None:
        """Сохраняет репо для просмотра данных."""
        self._repo_factory = repo_factory

    def get_df(self, table_name: base.TableName) -> pd.DataFrame:
        """Возвращает DataFrame по имени таблицы."""
        with self._repo_factory() as store:
            if (table := store.get_table(table_name)) is None:
                raise base.DataError(f"Таблицы {table_name} нет в хранилище")
            return table.df
