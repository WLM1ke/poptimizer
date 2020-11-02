"""Фабрика для создания таблиц."""
import types
from datetime import datetime
from typing import Final, Mapping, Type, cast

import pandas as pd

from poptimizer.data_di.domain import tables, trading_dates
from poptimizer.data_di.shared import domain

_TABLE_TYPES: Final = (trading_dates.TradingDates,)


AnyTable = tables.AbstractTable[domain.AbstractEvent]
Registry = Mapping[str, Type[AnyTable]]


class TablesFactory(domain.AbstractFactory[AnyTable]):
    """Фабрика, создающая все таблицы."""

    _types_mapping: Final[Registry] = types.MappingProxyType(
        {type_.group: cast(Type[AnyTable], type_) for type_ in _TABLE_TYPES},
    )

    def __call__(
        self,
        id_: domain.ID,
        mongo_dict: domain.StateDict,
    ) -> AnyTable:
        """Загружает таблицу по ID."""
        group = id_.group
        if (table_type := self._types_mapping.get(group)) is None:
            raise tables.WrongTableIDError(id_)

        df = cast(pd.DataFrame, mongo_dict.get("df"))
        timestamp = cast(datetime, mongo_dict.get("timestamp"))

        return table_type(id_, df, timestamp)
