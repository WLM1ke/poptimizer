"""Группа операций с таблицами, в конце которой осуществляется сохранение изменных данных."""
import pandas as pd

from poptimizer.data.domain import factories, model, repo
from poptimizer.data.ports import app, base, domain, outer


def _load_or_create_table(
    table_name: base.TableName,
    store: repo.Repo,
) -> model.Table:
    if (table := store.get_table(table_name)) is None:
        desc = store.get_description(table_name)
        table = factories.create_table(table_name, desc)
        store.add_table(table)
    return table


class EventsBus(app.AbstractEventsBus):
    """Шина для обработки сообщений."""

    def __init__(
        self,
        description_registry: app.AbstractTableDescriptionRegistry,
        db_session: outer.AbstractDBSession,
    ) -> None:
        """Сохраняет параметры для создания изолированных репо для каждой обработки события."""
        self._repo_params = (description_registry, db_session)

    def handle_event(self, message: domain.AbstractEvent) -> None:
        """Обработка сообщения и следующих за ним."""
        messages = [message]
        repo_params = self._repo_params
        while messages:
            message = messages.pop()
            with repo.Repo(*repo_params) as store:
                tables_dict = {
                    table_name: _load_or_create_table(table_name, store)
                    for table_name in message.tables_required
                }
                message.handle_event(tables_dict)
            messages.extend(message.new_events)


class Viewer(app.AbstractViewer):
    """Позволяет смотреть DataFrame по имени таблицы."""

    def __init__(
        self,
        description_registry: app.AbstractTableDescriptionRegistry,
        db_session: outer.AbstractDBSession,
    ) -> None:
        """Сохраняет репо для просмотра данных."""
        self._repo = repo.Repo(description_registry, db_session)

    def get_df(self, table_name: base.TableName) -> pd.DataFrame:
        """Возвращает DataFrame по имени таблицы."""
        with self._repo as store:
            if (table := store.get_table(table_name)) is None:
                raise base.DataError(f"Таблицы {table_name} нет в хранилище")
            return table.df
