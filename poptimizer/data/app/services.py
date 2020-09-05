"""Группа операций с таблицами, в конце которой осуществляется сохранение изменных данных."""
import asyncio
import contextlib
import itertools
from typing import AsyncIterator, List, Tuple

import pandas as pd

from poptimizer.data.domain import factories, model, repo
from poptimizer.data.ports import base, outer


@contextlib.asynccontextmanager
async def unit_of_work(db_session: outer.AbstractDBSession) -> AsyncIterator[repo.Repo]:
    """Одна транзакция в базу данных.

    Контекстный менеджер, возвращающий Репо для транзакций.
    """
    store = repo.Repo(db_session)
    try:
        yield store
    finally:
        await store.commit()


async def _load_or_create_table(
    table_name: base.TableName,
    store: repo.Repo,
) -> Tuple[base.TableName, model.Table]:
    async with store:
        if (table := await store.get_table(table_name)) is None:
            table = factories.create_table(table_name)
            store.add_table(table)
        return table_name, table


async def _handle_one_event(event: outer.AbstractEvent, store: repo.Repo) -> List[outer.AbstractEvent]:
    """Обрабатывает одно событие и возвращает  дочерние."""
    aws = [_load_or_create_table(table_name, store) for table_name in event.tables_required]
    tables_dict = dict(await asyncio.gather(*aws))
    event.handle_event(tables_dict)
    return event.new_events


class EventsBus(outer.AbstractEventsBus):
    """Шина для обработки сообщений."""

    def __init__(self, db_session: outer.AbstractDBSession) -> None:
        """Сохраняет параметры для создания изолированных UoW."""
        self._db_session = db_session

    async def handle_events(self, events: List[outer.AbstractEvent]) -> None:
        """Обработка сообщения и следующих за ним.

        Обработка сообщений идет поколениями - первое поколение генерирует поколение сообщений
        потомков и т.д. В рамках поколения обработка сообщений идет в несколько потоков с одной
        версией репо, что обеспечивает согласованность данных во всех потоках. После обработки
        поколения изменения сохраняются и создается новая версии репо для следующего поколения.
        """
        while events:
            async with unit_of_work(self._db_session) as store:
                aws = [_handle_one_event(event, store) for event in events]
                next_events = await asyncio.gather(*aws)
                events = list(itertools.chain.from_iterable(next_events))


class Viewer(outer.AbstractViewer):
    """Позволяет смотреть DataFrame по имени таблицы."""

    def __init__(self, db_session: outer.AbstractDBSession) -> None:
        """Сохраняет репо для просмотра данных."""
        self._db_session = db_session

    async def get_df(self, table_name: base.TableName) -> pd.DataFrame:
        """Возвращает DataFrame по имени таблицы."""
        if (table_tuple := await self._db_session.get(table_name)) is None:
            raise base.DataError(f"Таблицы {table_name} нет в хранилище")
        table = factories.recreate_table(table_tuple)
        return table.df
