"""Реализация репозиторий с таблицами."""
import weakref
from typing import List, MutableMapping, Set

import injector

from poptimizer import config
from poptimizer.data_di.domain import tables
from poptimizer.data_di.shared import entities, mapper

AnyTableFactory = tables.AbstractTableFactory[entities.AbstractEvent]
AnyTable = tables.AbstractTable[entities.AbstractEvent]


class NoFactoryError(config.POptimizerError):
    """Отсутствует фабрика для группы таблиц."""


class Repo:
    """Класс репозитория для хранения таблиц.

    Контекстный менеджер обеспечивающий сохранение измененных таблиц. С помощью identity_map
    обеспечивается корректная обработка запроса одной и той же таблицы из разных репо при их
    асинхронной обработке.
    """

    _identity_map: MutableMapping[
        entities.ID,
        AnyTable,
    ] = weakref.WeakValueDictionary()

    def __init__(
        self,
        db_session: injector.Inject[mapper.MongoDBSession],
        factories: injector.Inject[List[AnyTableFactory]],
    ) -> None:
        """Сохраняются ссылки на таблицы, которые были добавлены или взяты из репозитория."""
        self._session = db_session
        self._factories = {factory.group: factory for factory in factories}
        self._seen: Set[AnyTable] = set()

    def seen(self) -> Set[AnyTable]:
        """Возвращает виденные таблицы."""
        return self._seen

    async def get_table(self, table_id: entities.ID) -> AnyTable:
        """Берет таблицу из репозитория."""
        table = await self._load_table(table_id)
        self._seen.add(table)
        return table

    async def _load_table(self, table_id: entities.ID) -> AnyTable:
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

    async def _load_or_create(self, table_id: entities.ID) -> AnyTable:
        """Загружает из базы, а в случае отсутствия создается пустая таблица."""
        if (doc := await self._session.get(table_id)) is None:
            doc = {}
        group = table_id.group
        try:
            factory = self._factories[group]
        except KeyError:
            raise NoFactoryError(table_id)
        return factory.create_table(table_id, **doc)
