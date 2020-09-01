"""Группа операций с таблицами, в конце которой осуществляется сохранение изменных данных."""
from poptimizer.data.domain import factories, model, repo
from poptimizer.data.ports import app, base, events, outer


def _load_or_create_table(
    table_name: base.TableName,
    repository: repo.Repo,
) -> model.Table:
    if (table := repository.get_table(table_name)) is None:
        desc = repository.get_description(table_name)
        table = factories.create_table(table_name, desc)
        repository.add_table(table)
    return table


class EventsBus:
    """Шина для обработки сообщений."""

    def __init__(
        self,
        description_registry: app.AbstractTableDescriptionRegistry,
        db_session: outer.AbstractDBSession,
    ) -> None:
        """Создает изолированную сессию с базой данной и репо."""
        self._repo_params = (description_registry, db_session)

    def handle_event(self, message: events.AbstractEvent) -> None:
        """Обработка сообщения и его следующих за ним."""
        messages = [message]
        repo_params = self._repo_params
        while messages:
            message = messages.pop()
            with repo.Repo(*repo_params) as repository:
                tables_dict = {
                    table_name: _load_or_create_table(table_name, repository)
                    for table_name in message.tables_required
                }
                message.handle_event(tables_dict)
            messages.extend(message.new_events)
