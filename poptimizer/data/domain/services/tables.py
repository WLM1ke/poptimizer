"""Доменные службы, ответственные за обновление таблиц."""
import pandas as pd

import poptimizer.data.config
from poptimizer.data.domain import model
from poptimizer.data.domain.services import need_update
from poptimizer.data.ports import app, base, outer


def valid_index(df: pd.DataFrame, index_checks: app.IndexChecks) -> None:
    """Проверка индекса таблицы."""
    index = df.index
    if index_checks & app.IndexChecks.UNIQUE and not index.is_unique:
        raise base.DataError(f"Индекс не уникален\n{df}")
    if index_checks & app.IndexChecks.ASCENDING and not index.is_monotonic_increasing:
        raise base.DataError(f"Индекс не возрастает\n{df}")


def update_helper(table: model.Table, registry: app.AbstractTableDescriptionRegistry) -> None:
    """Обновляет вспомогательную таблицу."""
    if (helper_table := table.helper_table) is not None:
        update(helper_table, registry)


def valid_df(df_new: pd.DataFrame, df_old: pd.DataFrame) -> None:
    """Проверяет корректность новых данных."""
    df_new = df_new.reindex(df_old.index)
    try:
        pd.testing.assert_frame_equal(df_new, df_old)
    except AssertionError:
        raise base.DataError("Новые данные не соответствуют старым")


def get_update(table: model.Table, table_desc: app.TableDescription) -> pd.DataFrame:
    """Получает обновление и проверяет его корректность."""
    updater = table_desc.loader
    df_old = table.df
    if isinstance(updater, outer.AbstractLoader):
        df_new = updater(table.name)
    else:
        date = poptimizer.data.config.STATS_START
        if df_old is not None:
            date = df_old.index[-1].date()
        df_new = updater(table.name, date)
        if df_old is not None:
            df_new = pd.concat([df_old.iloc[:-1], df_new], axis=0)
    if df_old is not None and table_desc.validate:
        valid_df(df_new, df_old)
    return df_new


def update_main(table: model.Table, registry: app.AbstractTableDescriptionRegistry) -> None:
    """Обновляет данные основной таблицы."""
    table_desc = registry[table.name.group]
    df = get_update(table, table_desc)
    valid_index(df, table_desc.index_checks)
    table.df = df


def update(
    table: model.Table,
    registry: app.AbstractTableDescriptionRegistry,
    force: bool = False,
) -> None:
    """Обновляет таблицу."""
    update_helper(table, registry)
    if force or need_update.check(table):
        update_main(table, registry)


def force_update_table(table: model.Table, registry: app.AbstractTableDescriptionRegistry) -> None:
    """Принудительно обновляет таблицу."""
    update(table, registry, force=True)
