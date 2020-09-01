"""Фабрики по созданию объектов и их сериализации."""
from typing import Optional

from poptimizer.data.domain import model
from poptimizer.data.ports import base


def create_table(name: base.TableName, helper: Optional[model.Table]) -> model.Table:
    """Создает таблицу."""
    return model.Table(name=name, helper_table=helper)


def recreate_table(table_tuple: base.TableTuple, helper: Optional[model.Table]) -> model.Table:
    """Создает таблицу на основе данных и обновляет ее."""
    name = base.TableName(table_tuple.group, table_tuple.name)
    return model.Table(name, helper, table_tuple.df, table_tuple.timestamp)


def convent_to_tuple(table: model.Table) -> base.TableTuple:
    """Конвертирует объект в кортеж."""
    if (timestamp := table.timestamp) is None:
        raise base.DataError(f"Попытка сериализации пустой таблицы {table}")
    group, name = table.name
    return base.TableTuple(group=group, name=name, df=table.df, timestamp=timestamp)
