"""Фабрики по созданию объектов и их сериализации."""
from poptimizer.data.domain import model
from poptimizer.data.ports import app, base


def create_table(name: base.TableName, desc: app.TableDescription) -> model.Table:
    """Создает таблицу."""
    return model.Table(name=name, desc=desc)


def recreate_table(table_tuple: base.TableTuple, desc: app.TableDescription) -> model.Table:
    """Создает таблицу на основе данных и обновляет ее."""
    name = base.TableName(table_tuple.group, table_tuple.name)
    return model.Table(name, desc, table_tuple.df, table_tuple.timestamp)


def convent_to_tuple(table: model.Table) -> base.TableTuple:
    """Конвертирует объект в кортеж."""
    group, name = table.name
    if (timestamp := table.timestamp) is None:
        raise base.DataError(f"Попытка сериализации пустой таблицы {table.name}")
    return base.TableTuple(group=group, name=name, df=table.df, timestamp=timestamp)
