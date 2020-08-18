"""Реализации сессий доступа к базе данных."""
from typing import Iterable, Optional, Tuple

from poptimizer.data.core import ports
from poptimizer.data.core.ports import TableVars


class InMemoryDBSession(ports.AbstractDBSession):
    """Реализация сессии с хранением в памяти для тестов."""

    def __init__(self, tables_vars: Optional[Iterable[TableVars]] = None) -> None:
        """Создает хранилище в памяти."""
        self.committed = {}
        if tables_vars is not None:
            self.committed.update(
                {(table_vars["group"], table_vars["_id"]): table_vars for table_vars in tables_vars},
            )

    def get(self, name: Tuple[str, str]) -> Optional[TableVars]:
        """Выдает таблицы, переданные при создании."""
        return self.committed.get(name)

    def commit(self, tables_vars: Iterable[TableVars]) -> None:
        """Дополняет словарь таблиц, переданных при создании."""
        tables_dict = {
            (table_vars["group"], table_vars["_id"]): table_vars for table_vars in tables_vars
        }
        return self.committed.update(tables_dict)
