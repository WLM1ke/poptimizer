"""Запросы таблиц."""
import pandas as pd

from poptimizer.data.app.uow import UnitOfWork
from poptimizer.data.domain import factories, model
from poptimizer.data.domain.services import tables
from poptimizer.data.ports import app, base


def _load_or_create_table(
    table_name: base.TableName,
    app_config: app.Config,
    uow: UnitOfWork,
) -> model.Table:
    table = uow.repo.get(table_name)
    if table is None:
        desc = app_config.description_registry[table_name.group]
        table = factories.create_table(table_name, desc)
        uow.repo.add(table)
    return table


def get_df(
    table_name: base.TableName,
    app_config: app.Config,
    force_update: bool = False,
) -> pd.DataFrame:
    """Возвращает таблицу по наименованию."""
    with UnitOfWork(app_config.description_registry, app_config.db_session) as uow:
        helper_name = tables.get_helper_name(table_name)
        helper = None
        if helper_name is not None:
            helper = _load_or_create_table(helper_name, app_config, uow)
            tables.update(helper, helper=None)

        table = _load_or_create_table(table_name, app_config, uow)
        tables.update(table, helper, force_update)

        return table.df


def get_df_force_update(table_name: base.TableName, app_config: app.Config) -> pd.DataFrame:
    """Возвращает таблицу по наименованию с принудительным обновлением."""
    return get_df(table_name, app_config, force_update=True)
