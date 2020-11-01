"""Фабрика для создания таблиц."""
import types
from datetime import datetime
from typing import Final, Mapping, Type, TypedDict, cast

import pandas as pd

from poptimizer.data_di.domain import tables, trading_dates
from poptimizer.data_di.shared import domain

_TABLE_TYPES: Final = (trading_dates.TradingDates,)


class StateDict(TypedDict, total=False):
    """Внутренне состояние таблицы."""

    df: pd.DataFrame
    timestamp: datetime


AnyTable = tables.AbstractTable[domain.AbstractEvent]
Registry = Mapping[str, Type[AnyTable]]


class TablesFactory(domain.AbstractFactory[AnyTable, StateDict]):
    """Фабрика, создающая все таблицы."""

    _types_mapping: Final[Registry] = types.MappingProxyType(
        {type_.group: cast(Type[AnyTable], type_) for type_ in _TABLE_TYPES},
    )

    def __call__(
        self,
        id_: domain.ID,
        mongo_dict: StateDict,
    ) -> AnyTable:
        """Загружает таблицу по ID."""
        group = id_.group
        if (table_type := self._types_mapping.get(group)) is None:
            raise tables.WrongTableIDError(id_)

        return table_type(id_, **mongo_dict)
