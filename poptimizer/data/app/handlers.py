"""Запросы таблиц."""
import pandas as pd

from poptimizer.data.app import services
from poptimizer.data.domain import events, repo
from poptimizer.data.ports import app, base


def get_df(
    table_name: base.TableName,
    app_config: app.Config,
    force_update: bool = False,
) -> pd.DataFrame:
    """Возвращает таблицу по наименованию."""
    bus = services.EventsBus(app_config.description_registry, app_config.db_session)
    event = events.UpdateDataFrame(table_name, force_update)
    bus.handle_event(event)
    store = repo.Repo(app_config.description_registry, app_config.db_session)
    if (table := store.get(table_name)) is None:
        raise base.DataError(f"Таблицы {table_name} нет в хранилище")
    return table.df


def get_df_force_update(table_name: base.TableName, app_config: app.Config) -> pd.DataFrame:
    """Возвращает таблицу по наименованию с принудительным обновлением."""
    return get_df(table_name, app_config, force_update=True)
