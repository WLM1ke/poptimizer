"""Фабрики по созданию объектов и их сериализации."""
import pandas as pd

from poptimizer.data.core import ports
from poptimizer.data.core.domain import model


def create_table(name: model.TableName, df: pd.DataFrame) -> model.Table:
    """Создает таблицу."""
    return model.Table(name, df)


def recreate_table(table_tuple: ports.TableTuple) -> model.Table:
    """Создает таблицу на основе данных и обновляет ее."""
    group = model.TableGroup(table_tuple.group)
    id_ = model.TableId(table_tuple.id_)
    name = (group, id_)
    return model.Table(name, table_tuple.df, table_tuple.timestamp)


def convent_to_tuple(table: model.Table) -> ports.TableTuple:
    """Конвертирует объект в кортеж."""
    group, id_ = table.name
    return ports.TableTuple(group=group, id_=id_, df=table.df, timestamp=table.timestamp)
