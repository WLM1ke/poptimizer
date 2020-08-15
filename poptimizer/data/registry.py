"""Реестр типов таблиц."""
from types import MappingProxyType
from typing import NamedTuple, NewType, Tuple, Union

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


TRADING_DATES = TableSpec()

REGISTRY = MappingProxyType({TableGroup("trading_dates"): TRADING_DATES})


def get_tables_registry() -> MappingProxyType[TableGroup, TableSpec]:
    """Реестр существующих типов таблиц."""
    return REGISTRY
