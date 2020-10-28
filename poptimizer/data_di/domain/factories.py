"""Фабрики по созданию таблиц и их сериализации."""
from datetime import datetime
from typing import Optional

import pandas as pd
from injector import Inject

from poptimizer.data_di.adapters.gateways.trading_dates import TradingDatesGateway
from poptimizer.data_di.domain.trading_dates import TradingDates
from poptimizer.data_di.ports import tables


class TablesFactory:
    """Фабрика создания таблиц."""

    def __init__(
        self,
        trading_dates_gateway: Inject[TradingDatesGateway],
    ) -> None:
        """Создает mapping между наименованием группы и настройками для создания таблицы."""
        self._gateway = trading_dates_gateway

    def create_table(
        self,
        table_id: tables.TableID,
        df: Optional[pd.DataFrame] = None,
        timestamp: Optional[datetime] = None,
    ) -> TradingDates:
        """Создает таблицу на основе данных и обновляет ее."""
        return TradingDates(table_id, df, timestamp, self._gateway)
