"""Группа операций с таблицами, в конце которой осуществляется сохранение изменных данных."""
from poptimizer.data.domain import factories, model, repo
from poptimizer.data.ports import app, base, events, outer


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
        if exc_type is None:
            self._db_session.commit(self._repo.seen())

    @property
    def repo(self) -> repo.Repo:
        """Репо, хранящее информацию о виденных в рамках UoW таблицах."""
        return self._repo


def _load_or_create_table(
    table_name: base.TableName,
    registry: app.AbstractTableDescriptionRegistry,
    uow: UnitOfWork,
) -> model.Table:
    table = uow.repo.get(table_name)
    if table is None:
        desc = registry[table_name.group]
        table = factories.create_table(table_name, desc)
        uow.repo.add(table)
    return table


class EventsBus:
    """Шина для обработки сообщений."""

    def __init__(
        self,
        description_registry: app.AbstractTableDescriptionRegistry,
        db_session: outer.AbstractDBSession,
    ) -> None:
        """Создает изолированную сессию с базой данной и репо."""
        self._registry = description_registry
        self._db_session = db_session

    def handle_event(self, message: events.AbstractEvent) -> None:
        """Обработка сообщения и его следующих за ним."""
        messages = [message]
        registry = self._registry
        while messages:
            message = messages.pop()
            with UnitOfWork(registry, self._db_session) as uow:
                tables_dict = {
                    table_name: _load_or_create_table(table_name, registry, uow)
                    for table_name in message.tables_required
                }
                message.handle_event(tables_dict)
            messages.extend(message.new_events)
