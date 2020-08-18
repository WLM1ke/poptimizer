"""Запросы таблиц."""
from typing import Tuple, cast

import pandas as pd

from poptimizer.data.core.app import config
from poptimizer.data.core.domain import model, services

uow_factory = config.get_uow_factory()


def get_table(name: Tuple[str, str]) -> pd.DataFrame:
    """Возвращает таблицу по наименованию."""
    name = cast(model.TableName, name)
    with uow_factory() as repo:
        table = repo.get(name)
        if table is None:
            table = services.create_table(name)
            repo.add(table)
        return table.df
