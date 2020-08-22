"""Запросы таблиц."""
import pandas as pd

from poptimizer.data.core import ports
from poptimizer.data.core.domain import factories, repo, services


class UnitOfWork:
    """Группа операций с таблицами, в конце которой осуществляется сохранение изменных данных."""

    def __init__(self, db_session: ports.AbstractDBSession) -> None:
        """Создает изолированную сессию с базой данной и репо."""
        self._db_session = db_session
        self._repo = repo.Repo(db_session)

    def __enter__(self) -> "UnitOfWork":
        """Возвращает репо с таблицами."""
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:  # type: ignore
        """Сохраняет изменные данные в базу данных."""
        self._db_session.commit(self._repo.seen())

    @property
    def repo(self) -> repo.Repo:
        """Репо, хранящее информацию о виденных в рамках UoW таблицах."""
        return self._repo


def get_table(table_name: ports.TableName,
              db_session: ports.AbstractDBSession,
              updater: ports.AbstractUpdater) -> pd.DataFrame:
    """Возвращает таблицу по наименованию."""
    with UnitOfWork(db_session) as uow:
        table = uow.repo.get(table_name)
        if table is None:
            table = factories.create_table(table_name)
            uow.repo.add(table)
        services.update_table(table, updater)
        return table.df
