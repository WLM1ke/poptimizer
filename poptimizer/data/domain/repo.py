"""Реализация репозиторий с таблицами."""
from datetime import datetime
from typing import Dict, Iterable, NamedTuple, Optional

from poptimizer.data.domain import factories, model
from poptimizer.data.ports import app, base, outer


class TimedTable(NamedTuple):
    """Таблица и момент времени на момент загрузки или создания."""

    table: model.Table
    timestamp: Optional[datetime]


class Repo:
    """Класс репозитория для хранения таблиц."""

    def __init__(
        self,
        description_registry: app.AbstractTableDescriptionRegistry,
        db_session: outer.AbstractDBSession,
    ) -> None:
        """Сохраняются ссылки на таблицы, которые были добавлены или взяты из репозитория."""
        self._descriptions = description_registry
        self._session = db_session
        self._seen: Dict[base.TableName, TimedTable] = {}

    def add(self, table: model.Table) -> None:
        """Добавляет таблицу в репозиторий."""
        self._seen[table.name] = TimedTable(table, None)

    def get(self, table_name: base.TableName) -> Optional[model.Table]:
        """Берет таблицу из репозитория."""
        if (timed_table := self._seen.get(table_name)) is not None:
            return timed_table.table

        if (table_tuple := self._session.get(table_name)) is None:
            return None

        desc = self._descriptions[table_name.group]
        table = factories.recreate_table(table_tuple, desc)
        self._seen[table.name] = TimedTable(table, table.timestamp)

        return table

    def seen(self) -> Iterable[base.TableTuple]:
        """Возвращает данные о таблицах."""
        yield from (
            factories.convent_to_tuple(table)
            for table, timestamp in self._seen.values()
            if timestamp != table.timestamp
        )
