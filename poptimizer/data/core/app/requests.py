"""Запросы таблиц."""
import pandas as pd

from poptimizer.data.core import ports
from poptimizer.data.core.app import config
from poptimizer.data.core.domain import factories, model, services

uow_factory = config.get_uow_factory()


def get_table(table_name: ports.TableName) -> pd.DataFrame:
    """Возвращает таблицу по наименованию."""
    with uow_factory() as repo:
        updater = model.registry.get_specs(table_name).updater
        table = repo.get(table_name)
        if table is None:
            df = updater.get_update()
            table = factories.create_table(table_name, df)
            repo.add(table)
        elif services.need_update(table):
            table.df = updater.get_update()
        return table.df
