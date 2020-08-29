"""Доменные службы, ответственные за обновление таблиц."""
import pandas as pd

from poptimizer.data import ports
from poptimizer.data.domain import model
from poptimizer.data.domain.services import need_update


def valid_index(df: pd.DataFrame, index_checks: ports.IndexChecks) -> None:
    """Проверка индекса таблицы."""
    index = df.index
    if index_checks & ports.IndexChecks.UNIQUE and not index.is_unique:
        raise ports.DataError(f"Индекс не уникален\n{df}")
    if index_checks & ports.IndexChecks.ASCENDING and not index.is_monotonic_increasing:
        raise ports.DataError(f"Индекс не возрастает\n{df}")


def update_helper(table: model.Table, registry: ports.AbstractTableDescriptionRegistry) -> None:
    """Обновляет вспомогательную таблицу."""
    if (helper_table := table.helper_table) is not None:
        update_table(helper_table, registry)


def update_main(table: model.Table, registry: ports.AbstractTableDescriptionRegistry) -> None:
    """Обновляет данные основной таблицы."""
    table_desc = registry[table.name.group]
    updater = table_desc.updater
    df = updater(table.name)
    valid_index(df, table_desc.index_checks)
    table.df = df


def update_table(
    table: model.Table,
    registry: ports.AbstractTableDescriptionRegistry,
    force: bool = False,
) -> None:
    """Обновляет таблицу."""
    update_helper(table, registry)
    if force or need_update.check(table):
        update_main(table, registry)


def force_update_table(table: model.Table, registry: ports.AbstractTableDescriptionRegistry) -> None:
    """Принудительно обновляет таблицу."""
    update_table(table, registry, force=True)
