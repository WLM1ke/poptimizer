"""Таблица с торговыми датами."""
from datetime import datetime
from typing import Optional

import pandas as pd

from poptimizer.data_di.domain import events, ports, table, update


class TradingDates(table.AbstractTable[events.AppStarted, events.TradingDayEnded]):
    """Таблица с данными о торговых днях.

    Обрабатывает событие начала работы приложения.
    Инициирует событие в случае окончания очередного торгового дня.
    """

    def __init__(
        self,
        id_: table.TableID,
        df: Optional[pd.DataFrame],
        timestamp: Optional[datetime],
        gateway: ports.AbstractGateway,
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
            raise table.TableIndexError()
        if df_new.columns.tolist() != ["from", "till"]:
            raise table.TableIndexError()

    def _new_events(self) -> events.TradingDayEnded:
        """Событие окончания торгового дня."""
        if (df := self._df) is None:
            raise table.TableNeverUpdatedError(self._id)
        last_trading_day = df.loc[0, "till"]
        return events.TradingDayEnded(last_trading_day.date())
