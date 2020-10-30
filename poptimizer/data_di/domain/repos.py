"""Реализация репозиторий с таблицами."""
import weakref
from typing import Generic, MutableMapping, Set, TypeVar

from poptimizer.data_di.domain import tables
from poptimizer.data_di.shared import entities, mapper

Event = TypeVar("Event", bound=entities.AbstractEvent)


class Repo(Generic[Event]):
    """Класс репозитория для хранения таблиц.

    Контекстный менеджер обеспечивающий сохранение измененных таблиц. С помощью identity_map
    обеспечивается корректная обработка запроса одной и той же таблицы из разных репо при их
    асинхронной обработке.
    """

    _identity_map: MutableMapping[
        entities.ID,
        tables.AbstractTable[Event],
    ] = weakref.WeakValueDictionary()

    def __init__(
        self,
        db_session: mapper.MongoDBSession,
        factory: tables.AbstractTableFactory[Event],
    ) -> None:
        """Сохраняются ссылки на таблицы, которые были добавлены или взяты из репозитория."""
        self._session = db_session
        self._factory = factory
        self._seen: Set[tables.AbstractTable[Event]] = set()

    def seen(self) -> Set[tables.AbstractTable[Event]]:
        """Возвращает виденные таблицы."""
        return self._seen

    async def get_table(self, table_id: entities.ID) -> tables.AbstractTable[Event]:
        """Берет таблицу из репозитория."""
        table = await self._load_table(table_id)
        self._seen.add(table)
        return table

    async def _load_table(self, table_id: entities.ID) -> tables.AbstractTable[Event]:
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

    async def _load_or_create(self, table_id: entities.ID) -> tables.AbstractTable[Event]:
        """Загружает из базы, а в случае отсутствия создается пустая таблица."""
        if (doc := await self._session.get(table_id)) is None:
            doc = {}
        return self._factory.create_table(table_id, **doc)
