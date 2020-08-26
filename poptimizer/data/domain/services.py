"""Доменные службы, ответственные за обновление таблиц."""

import pandas as pd

from poptimizer.data import ports
from poptimizer.data.domain import model, trading_day


def rule_for_new_or_without_helper(table: model.Table) -> bool:
    """Правило обновления для таблиц без вспомогательной таблицы.

    - Если новая, то есть не содержит данных
    - Не обновлялась после возможного окончания последнего торгового дня
    """
    if (timestamp := table.timestamp) is None:
        return True
    return table.helper_table is None and timestamp < trading_day.potential_end()


def rule_for_new_or_with_helper(table: model.Table) -> bool:
    """Правило обновления для таблиц с вспомогательной таблицей.

    - Если новая, то есть не содержит данных
    - Не обновлялась после реального окончания последнего торгового дня из вспомогательной таблицы
    """
    if (timestamp := table.timestamp) is None:
        return True
    return table.helper_table is not None and timestamp < trading_day.real_end(table.helper_table)


def need_update(table: model.Table) -> bool:
    """Нужно ли обновлять данные о диапазоне доступных торговых дат.

    Если последние обновление было раньше публикации данных о последних торгах, то требуется
    обновление.
    """
    check_func = (
        rule_for_new_or_without_helper,
        rule_for_new_or_with_helper,
    )
    return any(func(table) for func in check_func)


def valid_index(df: pd.DataFrame, index_checks: ports.IndexChecks) -> None:
    """Проверка индекса таблицы."""
    index = df.index
    if index_checks & ports.IndexChecks.UNIQUE and not index.is_unique:
        raise ports.DataError("Индекс не уникален")
    if index_checks & ports.IndexChecks.ASCENDING and not index.is_monotonic_increasing:
        raise ports.DataError("Индекс не не возрастает")


def update_table(table: model.Table, registry: ports.AbstractTableDescriptionRegistry) -> None:
    """Обновляет таблицу."""
    if (helper_table := table.helper_table) is not None:
        update_table(helper_table, registry)
    if need_update(table):
        table_desc = registry[table.name.group]
        updater = table_desc.updater
        df = updater(table.name)
        valid_index(df, table_desc.index_checks)
        table.df = df
