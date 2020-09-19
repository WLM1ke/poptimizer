"""Реализация репозиторий с таблицами."""
import weakref
from datetime import datetime
from typing import Dict, MutableMapping, Optional, Set

from poptimizer.data.domain import factories, model
from poptimizer.data.ports import outer


class Repo:
    """Класс репозитория для хранения таблиц.

    Контекстный менеджер обеспечивающий блокировку для проведения атомарных операций по добавлению и
    извлечению таблиц.
    """

    _identity_map: MutableMapping[outer.TableName, model.Table] = weakref.WeakValueDictionary()
    _timestamps: Dict[outer.TableName, Optional[datetime]] = {}

    def __init__(self, db_session: outer.AbstractDBSession) -> None:
        """Сохраняются ссылки на таблицы, которые были добавлены или взяты из репозитория."""
        self._session = db_session
        self._seen: Set[outer.TableName] = set()

    async def get_table(self, table_name: outer.TableName) -> Optional[model.Table]:
        """Берет таблицу из репозитория."""
        self._seen.add(table_name)

        if (table_old := self._identity_map.get(table_name)) is not None:
            return table_old

        if (table_tuple := await self._session.get(table_name)) is None:
            table = factories.create_table(table_name)
        else:
            table = factories.recreate_table(table_tuple)

        if (table_old := self._identity_map.get(table_name)) is not None:
            return table_old

        self._identity_map[table_name] = table
        self._timestamps[table_name] = table.timestamp
        weakref.finalize(table, self._timestamps.pop, table_name)

        return table

    async def commit(self) -> None:
        """Сохраняет изменения в базу данных."""
        dirty = []
        for table_name in self._seen:
            table = self._identity_map[table_name]
            if self._timestamps[table_name] != table.timestamp:
                dirty.append(factories.convent_to_tuple(table))
                self._timestamps[table_name] = table.timestamp

        await self._session.commit(dirty)
