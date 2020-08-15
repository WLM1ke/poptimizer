"""Менеджер таблиц - обновляет таблицу при необходимости."""
from poptimizer.data.registry import get_specs
from poptimizer.data.table import Table


def table_updater(table: Table) -> None:
    """Обновляет таблицу при необходимости."""
    spec = get_specs(table.name)
    if spec.need_update_func(table.timestamp):
        table.df = spec.get_update_func()
