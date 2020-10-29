"""Фабрики по созданию таблиц и их сериализации."""
from datetime import datetime
from typing import Optional, cast

import pandas as pd
from injector import Inject

from poptimizer.data_di.adapters.gateways.trading_dates import TradingDatesGateway
from poptimizer.data_di.domain import events
from poptimizer.data_di.domain.trading_dates import TradingDates
from poptimizer.data_di.shared import entities


class TablesFactory:
    """Фабрика создания таблиц."""

    def __init__(
        self,
        trading_dates_gateway: Inject[TradingDatesGateway],
    ) -> None:
        """Сохраняет нужный gateway."""
        self._gateway = trading_dates_gateway

    def create_table(
        self,
        table_id: entities.ID,
        df: Optional[pd.DataFrame] = None,
        timestamp: Optional[datetime] = None,
    ) -> events.AllTablesTypes:
        """Создает таблицу на основе данных и обновляет ее."""
        return cast(events.AllTablesTypes, TradingDates(table_id, df, timestamp, self._gateway))
