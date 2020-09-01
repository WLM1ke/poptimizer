"""Группа операций с таблицами, в конце которой осуществляется сохранение изменных данных."""
from poptimizer.data.domain import repo
from poptimizer.data.ports import app, outer


class UnitOfWork:
    """Группа операций с таблицами, в конце которой осуществляется сохранение изменных данных."""

    def __init__(
        self,
        description_registry: app.AbstractTableDescriptionRegistry,
        db_session: outer.AbstractDBSession,
    ) -> None:
        """Создает изолированную сессию с базой данной и репо."""
        self._db_session = db_session
        self._repo = repo.Repo(description_registry, db_session)

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
