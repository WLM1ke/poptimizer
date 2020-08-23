"""Фабрики по созданию объектов и их сериализации."""
from typing import Optional

from poptimizer.data.core import ports
from poptimizer.data.core.domain import model


def get_helper_name(name: ports.TableName) -> Optional[ports.TableName]:
    """Имя вспомогательной таблицы."""
    if name.group != ports.TRADING_DATES:
        return ports.TableName(ports.TRADING_DATES, ports.TRADING_DATES)
    return None


def create_table(name: ports.TableName, helper: Optional[model.Table]) -> model.Table:
    """Создает таблицу."""
    return model.Table(name=name, helper_table=helper)


def recreate_table(table_tuple: ports.TableTuple, helper: Optional[model.Table]) -> model.Table:
    """Создает таблицу на основе данных и обновляет ее."""
    name = ports.TableName(table_tuple.group, table_tuple.name)
    return model.Table(name, helper, table_tuple.df, table_tuple.timestamp)


def convent_to_tuple(table: model.Table) -> ports.TableTuple:
    """Конвертирует объект в кортеж."""
    if (timestamp := table.timestamp) is None:
        raise ports.DataError(f"Попытка сериализации пустой таблицы {table}")
    group, name = table.name
    return ports.TableTuple(group=group, name=name, df=table.df, timestamp=timestamp)
