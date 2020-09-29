"""Реализация репозиторий с таблицами."""
import weakref
from types import TracebackType
from typing import AsyncContextManager, MutableMapping, Optional, Set, Type

from poptimizer.data.domain import factories, model
from poptimizer.data.ports import outer


class Repo(AsyncContextManager["Repo"]):
    """Класс репозитория для хранения таблиц.

    Контекстный менеджер обеспечивающий сохранение измененных таблиц. С помощью identity_map
    обеспечивается корректная обработка запроса одной и той же таблицы из разных репо при их
    асинхронной обработке.
    """

    _identity_map: MutableMapping[outer.TableName, model.Table] = weakref.WeakValueDictionary()

    def __init__(self, db_session: outer.AbstractDBSession) -> None:
        """Сохраняются ссылки на таблицы, которые были добавлены или взяты из репозитория."""
        self._session = db_session
        self._seen: Set[model.Table] = set()

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
        for seen_table in self._seen:
            if seen_table.is_dirty():
                dirty.append(factories.convent_to_tuple(seen_table))
                seen_table.clear()

        await self._session.commit(dirty)

    async def get_table(self, table_name: outer.TableName) -> model.Table:
        """Берет таблицу из репозитория."""
        table = await self._load_table(table_name)
        self._seen.add(table)
        return table

    async def _load_table(self, table_name: outer.TableName) -> model.Table:
        """Загрузка таблицы.

        - Синхронно загружается из identity map
        - Если отсутствует, то асинхронно загружается из базы или создается новая
        - Из-за асинхронности снова проверяется наличие в identity map
        - При отсутствии происходит обновление identity map
        """
        if (table_old := self._identity_map.get(table_name)) is not None:
            return table_old

        table = await self._load_or_create(table_name)

        if (table_old := self._identity_map.get(table_name)) is not None:
            return table_old

        self._identity_map[table_name] = table

        return table

    async def _load_or_create(self, table_name: outer.TableName) -> model.Table:
        """Загружает из базы, а в случае отсутствия создается пустая таблица."""
        if (table_tuple := await self._session.get(table_name)) is None:
            table = factories.create_table(table_name)
        else:
            table = factories.recreate_table(table_tuple)
        return table
