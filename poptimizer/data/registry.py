"""Реестр типов таблиц."""
from datetime import datetime
from types import MappingProxyType
from typing import Callable, NamedTuple, NewType, Optional, Tuple, Union

import pandas as pd

from poptimizer.data.updaters import trading_dates

TableGroup = NewType("TableGroup", str)
TableId = NewType("TableId", str)
# Наименование таблицы состоит из наименования группы и при наличии многих элементов в группе id
TableName = Union[Tuple[TableGroup], Tuple[TableGroup, TableId]]


class TableSpec(NamedTuple):
    """Описание разновидности таблицы с данными, особенностей обновления и валидации.

    - множество таблиц данного типа
    - возможность инкрементального обновления или только полной загрузки
    - уникальный индекс
    - возрастающий индекс
    """

    need_update_func: Callable[[Optional[datetime]], bool]
    get_update_func: Callable[[], pd.DataFrame]


TRADING_DATES = TableSpec(
    need_update_func=trading_dates.need_update, get_update_func=trading_dates.get_update,
)

REGISTRY = MappingProxyType({TableGroup("trading_dates"): TRADING_DATES})


def get_specs(name: TableName) -> TableSpec:
    """Реестр существующих типов таблиц."""
    return REGISTRY[name[0]]
