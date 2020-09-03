"""Запросы таблиц."""
import pandas as pd

from poptimizer.data import config
from poptimizer.data.domain import events
from poptimizer.data.ports import base


def get_df(
    table_name: base.TableName,
    force_update: bool = False,
) -> pd.DataFrame:
    """Возвращает таблицу по наименованию."""
    event = events.UpdateDataFrame(table_name, force_update)
    config.EVENTS_BUS.handle_event(event)
    return config.VIEWER.get_df(table_name)
