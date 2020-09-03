"""Реализация репозиторий с таблицами."""
from datetime import datetime
from typing import Dict, NamedTuple, Optional

from poptimizer.data.domain import factories, model
from poptimizer.data.ports import base, outer


class TimedTable(NamedTuple):
    """Таблица и момент времени на момент загрузки или создания."""

    table: model.Table
    timestamp: Optional[datetime]


class Repo:
    """Класс репозитория для хранения таблиц."""

    def __init__(self, db_session: outer.AbstractDBSession) -> None:
        """Сохраняются ссылки на таблицы, которые были добавлены или взяты из репозитория."""
        self._session = db_session
        self._seen: Dict[base.TableName, TimedTable] = {}

    def __enter__(self) -> "Repo":
        """Возвращает репо с таблицами."""
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:  # type: ignore
        """Сохраняет изменные данные в базу данных."""
        if exc_type is None:
            for_commit = (
                factories.convent_to_tuple(table)
                for table, timestamp in self._seen.values()
                if timestamp != table.timestamp
            )
            self._session.commit(for_commit)
        self._seen.clear()

    def add_table(self, table: model.Table) -> None:
        """Добавляет таблицу в репозиторий."""
        self._seen[table.name] = TimedTable(table, None)

    def get_table(self, table_name: base.TableName) -> Optional[model.Table]:
        """Берет таблицу из репозитория."""
        if (timed_table := self._seen.get(table_name)) is not None:
            return timed_table.table

        if (table_tuple := self._session.get(table_name)) is None:
            return None

        table = factories.recreate_table(table_tuple)
        self._seen[table.name] = TimedTable(table, table.timestamp)

        return table
