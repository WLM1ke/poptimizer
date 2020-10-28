"""Реализация репозиторий с таблицами."""
import asyncio
import weakref
from types import TracebackType
from typing import AsyncContextManager, MutableMapping, Optional, Set, Type

from injector import Inject

from poptimizer import config
from poptimizer.data_di.domain import events, factories
from poptimizer.data_di.shared import entity, mapper

PACKAGE = "data"


class WrongTableIDError(config.POptimizerError):
    """Запрошена таблица с некорректным ID."""


class Repo(AsyncContextManager["Repo"]):
    """Класс репозитория для хранения таблиц.

    Контекстный менеджер обеспечивающий сохранение измененных таблиц. С помощью identity_map
    обеспечивается корректная обработка запроса одной и той же таблицы из разных репо при их
    асинхронной обработке.
    """

    _identity_map: MutableMapping[
        entity.ID,
        events.AllTablesTypes,
    ] = weakref.WeakValueDictionary()

    def __init__(
        self,
        db_session: Inject[mapper.MongoDBSession],
        factory: Inject[factories.TablesFactory],
    ) -> None:
        """Сохраняются ссылки на таблицы, которые были добавлены или взяты из репозитория."""
        self._session = db_session
        self._factory = factory
        self._seen: Set[events.AllTablesTypes] = set()

    async def __aenter__(self) -> "Repo":
        """Возвращает репо с таблицами."""
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Сохраняет изменные данные в базу данных."""
        dirty = []
        commit = self._session.commit
        for seen_table in self._seen:
            if doc := seen_table.changed_state():
                dirty.append(commit(seen_table.id_, doc))
                seen_table.clear()

        await asyncio.gather(*dirty)

    async def get_table(self, table_id: entity.ID) -> events.AllTablesTypes:
        """Берет таблицу из репозитория."""
        if table_id.package != PACKAGE:
            raise WrongTableIDError(table_id)
        table = await self._load_table(table_id)
        self._seen.add(table)
        return table

    async def _load_table(self, table_id: entity.ID) -> events.AllTablesTypes:
        """Загрузка таблицы.

        - Синхронно загружается из identity map
        - Если отсутствует, то асинхронно загружается из базы или создается новая
        - Из-за асинхронности снова проверяется наличие в identity map
        - При отсутствии происходит обновление identity map
        """
        if (table_old := self._identity_map.get(table_id)) is not None:
            return table_old

        table = await self._load_or_create(table_id)

        if (table_old := self._identity_map.get(table_id)) is not None:
            return table_old

        self._identity_map[table_id] = table

        return table

    async def _load_or_create(self, table_id: entity.ID) -> events.AllTablesTypes:
        """Загружает из базы, а в случае отсутствия создается пустая таблица."""
        if (doc := await self._session.get(table_id)) is None:
            doc = {}
        return self._factory.create_table(table_id, **doc)
