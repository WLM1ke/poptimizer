"""Фабрика для создания таблиц."""
import types
from datetime import datetime
from typing import Final, Tuple, Type, cast

import pandas as pd

from poptimizer.data_di.domain.tables import base, indexes, quotes, securities, trading_dates
from poptimizer.data_di.shared import domain

AnyTable = base.AbstractTable[domain.AbstractEvent]
AllTableTypes = Tuple[Type[AnyTable], ...]


_TABLE_TYPES: Final[AllTableTypes] = cast(
    AllTableTypes,
    (trading_dates.TradingDates, securities.Securities, quotes.Quotes, indexes.Indexes),
)


class TablesFactory(domain.AbstractFactory[AnyTable]):
    """Фабрика, создающая все таблицы."""

    _types_mapping: Final = types.MappingProxyType(
        {cast(str, type_.group): type_ for type_ in _TABLE_TYPES},
    )

    def __call__(
        self,
        id_: domain.ID,
        mongo_dict: domain.StateDict,
    ) -> AnyTable:
        """Загружает таблицу по ID."""
        group = id_.group
        if (table_type := self._types_mapping.get(group)) is None:
            raise base.TableIWrongDError(id_)

        df = cast(pd.DataFrame, mongo_dict.get("df"))
        timestamp = cast(datetime, mongo_dict.get("timestamp"))

        return table_type(id_, df, timestamp)
