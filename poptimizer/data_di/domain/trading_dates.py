"""Таблица с торговыми датами."""
from datetime import datetime
from typing import ClassVar, List, Optional

import pandas as pd
from injector import Inject

from poptimizer.data_di.adapters.gateways.trading_dates import TradingDatesGateway
from poptimizer.data_di.domain import events, tables, update
from poptimizer.data_di.ports import gateways
from poptimizer.data_di.shared import entities


class TradingDates(tables.AbstractTable[events.AppStarted]):
    """Таблица с данными о торговых днях.

    Обрабатывает событие начала работы приложения.
    Инициирует событие в случае окончания очередного торгового дня.
    """

    def __init__(
        self,
        id_: entities.ID,
        df: Optional[pd.DataFrame],
        timestamp: Optional[datetime],
        gateway: gateways.AbstractGateway,
    ):
        """Использует gateway для загрузки обновленных данных."""
        super().__init__(id_, df, timestamp)
        self._gateway = gateway

    def _update_cond(self, event: events.AppStarted) -> bool:
        """Обновляет, если последняя дата обновления после потенциального окончания торгового дня."""
        return update.trading_day_potential_end_policy(self._timestamp)

    async def _prepare_df(self, event: events.AppStarted) -> pd.DataFrame:
        """Загружает новый DataFrame."""
        return await self._gateway.get()

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Проверка корректности индекса и заголовков."""
        if df_new.index.tolist() != [0]:
            raise tables.TableIndexError()
        if df_new.columns.tolist() != ["from", "till"]:
            raise tables.TableIndexError()

    def _new_events(self) -> List[entities.AbstractEvent]:
        """Событие окончания торгового дня."""
        if (df := self._df) is None:
            raise tables.TableNeverUpdatedError(self._id)
        last_trading_day = df.loc[0, "till"]
        return [events.TradingDayEnded(last_trading_day.date())]


class TablesFactory(tables.AbstractTableFactory[events.AppStarted]):
    """Фабрика создания таблиц."""

    group: ClassVar[str] = "trading_dates"

    def __init__(
        self,
        trading_dates_gateway: Inject[TradingDatesGateway],
    ) -> None:
        """Сохраняет нужный gateway."""
        self._gateway = trading_dates_gateway

    def _create_table(
        self,
        table_id: entities.ID,
        df: Optional[pd.DataFrame] = None,
        timestamp: Optional[datetime] = None,
    ) -> tables.AbstractTable[events.AppStarted]:
        """Создает таблицу определенного типа."""
        return TradingDates(table_id, df, timestamp, self._gateway)
