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


def valid_df(df_new: pd.DataFrame, df_old: pd.DataFrame, table_desc: ports.TableDescription) -> None:
    """Проверяет корректность новых данных."""
    val_type = table_desc.validation_type

    if val_type is ports.ValType.NO_VAL:
        return None
    elif val_type is ports.ValType.LAST:
        df_new = df_new.iloc[:1]
        df_old = df_old.iloc[-1:]
    elif val_type is ports.ValType.ALL:
        df_new = df_new.reindex(df_old.index)

    try:
        pd.testing.assert_frame_equal(df_new, df_old)
    except AssertionError as error:
        raise ports.DataError(error.args)

    return None


def get_update(table: model.Table, table_desc: ports.TableDescription) -> pd.DataFrame:
    """Получает обновление и проверяет его корректность."""
    updater = table_desc.updater
    df_new = updater(table.name)
    df_old = table.df
    valid_df(df_new, df_old, table_desc)
    return df_new


def update_main(table: model.Table, registry: ports.AbstractTableDescriptionRegistry) -> None:
    """Обновляет данные основной таблицы."""
    table_desc = registry[table.name.group]
    df = get_update(table, table_desc)
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
