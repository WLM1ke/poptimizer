"""Фабрики по созданию таблиц и их сериализации."""
from datetime import datetime

import pandas as pd
from injector import Inject

from poptimizer.data_di.adapters.gateways.trading_dates import TradingDatesGateway
from poptimizer.data_di.ports import table
from poptimizer.data_di.domain.trading_dates import TradingDates


class TablesFactory:
    """Фабрика создания таблиц."""

    def __init__(
        self,
        trading_dates_gateway: Inject[TradingDatesGateway],
    ) -> None:
        """Создает mapping между наименованием группы и настройками для создания таблицы."""
        self._table_types_mapping = {
            "trading_dates": (TradingDates, trading_dates_gateway),
        }

    def create_new_table(self, table_id: table.TableID) -> table.AbstractTable:
        """Создает пустую новую таблицу."""
        group = table_id.group
        table_type, *gateways = self._table_types_mapping[group]
        return table_type(table_id, None, None, *gateways)

    def recreate_table(
        self,
        table_id: table.TableID,
        df: pd.DataFrame,
        timestamp: datetime,
    ) -> table.AbstractTable:
        """Создает таблицу на основе данных и обновляет ее."""
        group = table_id.group
        table_type, *gateways = self._table_types_mapping[group]
        return table_type(table_id, df, timestamp, *gateways)
