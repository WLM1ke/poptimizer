"""Реализация репозиторий с таблицами."""
from datetime import datetime
from typing import Dict, Iterable, NamedTuple, Optional

from poptimizer.data.core import ports
from poptimizer.data.core.domain import factories, model


class TimedTable(NamedTuple):
    """Таблица и момент времени на момент загрузки или создания."""

    table: model.Table
    timestamp: Optional[datetime]


class Repo:
    """Класс репозитория для хранения таблиц."""

    def __init__(self, session: ports.AbstractDBSession) -> None:
        """Сохраняются ссылки на таблицы, которые были добавлены или взяты из репозитория."""
        self._session = session
        self._seen: Dict[ports.TableName, TimedTable] = {}

    def add(self, table: model.Table) -> None:
        """Добавляет таблицу в репозиторий."""
        self._seen[table.name] = TimedTable(table, table.timestamp)

    def get(self, name: ports.TableName) -> model.Table:
        """Берет таблицу из репозитория.

        При необходимости создает ее.
        """
        if (timed_table := self._seen.get(name)) is not None:
            return timed_table.table

        helper = self._load_helper(name)
        if (table := self._load_main(name, helper)) is not None:
            return table

        return self._create_main(name, helper)

    def seen(self) -> Iterable[ports.TableTuple]:
        """Возвращает данные о таблицах."""
        yield from (
            factories.convent_to_tuple(table)
            for table, timestamp in self._seen.values()
            if timestamp != table.timestamp
        )

    def _load_helper(self, name: ports.TableName) -> Optional[model.Table]:
        helper = None
        if (helper_name := factories.get_helper_name(name)) is not None:
            helper = self.get(helper_name)
        return helper

    def _load_main(self, name: ports.TableName, helper: Optional[model.Table]) -> Optional[model.Table]:
        if (table_tuple := self._session.get(name)) is not None:
            table = factories.recreate_table(table_tuple, helper)
            self.add(table)
            return table
        return None

    def _create_main(self, name: ports.TableName, helper: Optional[model.Table]) -> model.Table:
        table = factories.create_table(name, helper)
        self.add(table)
        return table
