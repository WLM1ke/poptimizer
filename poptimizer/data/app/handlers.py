"""Запросы таблиц."""
import pandas as pd

from poptimizer.data.domain import events
from poptimizer.data.ports import base, outer


def get_df(
    table_name: base.TableName,
    app_config: outer.Config,
    force_update: bool = False,
) -> pd.DataFrame:
    """Возвращает таблицу по наименованию."""
    bus = app_config.event_bus
    event = events.UpdateDataFrame(table_name, force_update)
    bus.handle_event(event)
    viewer = app_config.viewer
    return viewer.get_df(table_name)


def get_df_force_update(table_name: base.TableName, app_config: outer.Config) -> pd.DataFrame:
    """Возвращает таблицу по наименованию с принудительным обновлением."""
    return get_df(table_name, app_config, force_update=True)
