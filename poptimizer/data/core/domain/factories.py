"""Фабрики по созданию объектов и их сериализации."""
import pandas as pd

from poptimizer.data.core import ports
from poptimizer.data.core.domain import model


def create_table(name: ports.TableName, df: pd.DataFrame) -> model.Table:
    """Создает таблицу."""
    return model.Table(name, df)


def recreate_table(table_tuple: ports.TableTuple) -> model.Table:
    """Создает таблицу на основе данных и обновляет ее."""
    name = ports.TableName(table_tuple.group, table_tuple.name)
    return model.Table(name, table_tuple.df, table_tuple.timestamp)


def convent_to_tuple(table: model.Table) -> ports.TableTuple:
    """Конвертирует объект в кортеж."""
    group, name = table.name
    return ports.TableTuple(group=group, name=name, df=table.df, timestamp=table.timestamp)
