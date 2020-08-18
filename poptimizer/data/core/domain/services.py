"""Менеджер таблиц - обновляет таблицу при необходимости."""
from datetime import datetime

import pandas as pd

from poptimizer.data.core.domain import model


def create_table(name: model.TableName) -> model.Table:
    """Создает таблицу."""
    try:
        spec = model.registry.get_specs(name)
    except KeyError:
        raise model.TableError(f"Имя отсутствует в реестре - {name}")
    updater = spec.updater
    df = updater.get_update()
    return model.Table(name, df)


def recreate_table(name: model.TableName, df: pd.DataFrame, timestamp: datetime) -> model.Table:
    """Создает таблицу на основе данных и обновляет ее."""
    table = model.Table(name, df, timestamp)
    spec = model.registry.get_specs(table.name)
    updater = spec.updater
    if updater.need_update(table.timestamp):
        table.df = updater.get_update()
    return table
