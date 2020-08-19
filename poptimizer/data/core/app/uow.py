"""Группа операций с таблицами."""
from typing import Callable

from poptimizer.data.core import ports
from poptimizer.data.core.app import repo
from poptimizer.data.infrastructure import db


class UnitOfWork:
    """Группа операций с таблицами, в конце которой осуществляется сохранение изменных данных."""

    def __init__(self, db_factory: Callable[[], ports.AbstractDBSession] = db.MongoDBSession) -> None:
        """Создает изолированную сессию с базой данной и репо."""
        self._db = db_factory()
        self._repo = repo.Repo(self._db)

    def __enter__(self) -> repo.Repo:
        """Возвращает репо с таблицами."""
        return self._repo

    def __exit__(self, exc_type, exc_value, traceback) -> None:  # type: ignore
        """Сохраняет изменные данные в базу данных."""
        self._db.commit(self._repo.seen())
