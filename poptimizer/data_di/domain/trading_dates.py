"""Таблица с торговыми датами."""
from typing import ClassVar, Final, List

import pandas as pd

from poptimizer.data_di.adapters.gateways import moex
from poptimizer.data_di.domain import events, tables, update
from poptimizer.data_di.shared import domain


class TradingDates(tables.AbstractTable[events.AppStarted]):
    """Таблица с данными о торговых днях.

    Обрабатывает событие начала работы приложения.
    Инициирует событие в случае окончания очередного торгового дня.
    """

    group: ClassVar[str] = "trading_dates"
    _gateway: Final = moex.TradingDatesGateway()

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

    def _new_events(self) -> List[domain.AbstractEvent]:
        """Событие окончания торгового дня."""
        if (df := self._df) is None:
            raise tables.TableNeverUpdatedError(self._id)
        last_trading_day = df.loc[0, "till"]
        return [events.TradingDayEnded(last_trading_day.date())]
