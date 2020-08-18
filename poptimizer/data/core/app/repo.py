"""Инициализация реестра таблиц и реализация репозиторий с таблицами."""
from typing import Dict, Iterable, Optional

from poptimizer.data.core import ports
from poptimizer.data.core.domain import model, services


def _convent_to_table(table_vars: ports.TableVars) -> model.Table:
    group = model.TableGroup(table_vars["group"])
    id_ = table_vars["_id"]
    df = table_vars["df"]
    timestamp = table_vars["timestamp"]
    name = (model.TableGroup(group), model.TableId(id_))
    return services.recreate_table(name, df, timestamp)


def _convent_to_vars(table: model.Table) -> ports.TableVars:
    group, id_ = table.name
    return ports.TableVars(group=group, _id=id_, df=table.df, timestamp=table.timestamp)


class Repo:
    """Класс репозитория для хранения таблиц."""

    def __init__(self, session: ports.AbstractDBSession) -> None:
        """Сохраняются ссылки на таблицы, которые были добавлены или взяты из репозитория."""
        self._session = session
        self._seen: Dict[model.TableName, model.Table] = {}

    def add(self, table: model.Table) -> None:
        """Добавляет таблицу в репозиторий."""
        self._seen[table.name] = table

    def get(self, name: model.TableName) -> Optional[model.Table]:
        """Берет таблицу из репозитория."""
        if (table := self._seen.get(name)) is not None:
            return table
        if (table_vars := self._session.get(name)) is not None:
            table = _convent_to_table(table_vars)
            self.add(table)
            return table
        return None

    def seen(self) -> Iterable[ports.TableVars]:
        """Возвращает данные о таблицах."""
        yield from (_convent_to_vars(table) for table in self._seen.values())
