"""Запросы таблиц."""
import pandas as pd

from poptimizer.data import ports
from poptimizer.data.app import config
from poptimizer.data.domain import repo
from poptimizer.data.domain.services import tables


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


def get_table(table_name: ports.TableName, app_config: config.AppConfig) -> pd.DataFrame:
    """Возвращает таблицу по наименованию."""
    with UnitOfWork(app_config.db_session) as uow:
        table = uow.repo.get(table_name)
        tables.update_table(table, app_config.description_registry)
        return table.df


def get_table_force_update(table_name: ports.TableName, app_config: config.AppConfig) -> pd.DataFrame:
    """Возвращает таблицу по наименованию с принудительным обновлением."""
    with UnitOfWork(app_config.db_session) as uow:
        table = uow.repo.get(table_name)
        tables.force_update_table(table, app_config.description_registry)
        return table.df
