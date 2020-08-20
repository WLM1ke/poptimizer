"""Запросы таблиц."""
from typing import Tuple, cast

import pandas as pd

from poptimizer.data.core.app import config
from poptimizer.data.core.domain import factories, model, services

uow_factory = config.get_uow_factory()


def get_table(name: Tuple[str, str]) -> pd.DataFrame:
    """Возвращает таблицу по наименованию."""
    name = cast(model.TableName, name)
    with uow_factory() as repo:
        updater = model.registry.get_specs(name).updater
        table = repo.get(name)
        if table is None:
            df = updater.get_update()
            table = factories.create_table(name, df)
            repo.add(table)
        elif services.need_update(table):
            table.df = updater.get_update()
        return table.df
