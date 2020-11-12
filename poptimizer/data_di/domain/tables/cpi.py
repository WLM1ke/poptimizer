"""Таблица с индексом потребительской инфляции."""
from datetime import timedelta
from typing import ClassVar, Final, List

import pandas as pd

from poptimizer.data_di.adapters.gateways import cpi
from poptimizer.data_di.domain import events
from poptimizer.data_di.domain.tables import base, checks
from poptimizer.data_di.shared import domain


class CPI(base.AbstractTable[events.TradingDayEnded]):
    """Таблица с индексами на закрытие торгового дня."""

    group: ClassVar[base.GroupName] = base.CPI
    _gateway: Final = cpi.CPIGateway()

    def _update_cond(self, event: events.TradingDayEnded) -> bool:
        """Инфляция обновляется при отсутствии или окончание очередного месяца."""
        if (df := self._df) is None:
            return True

        last_cpi_month = df.index[-1].month
        last_full_month = (event.date.replace(day=1) - timedelta(days=-1)).month

        if last_cpi_month != last_full_month:
            return True

        return False

    async def _prepare_df(self, event: events.TradingDayEnded) -> pd.DataFrame:
        """Загружает новый DataFrame."""
        return await self._gateway.get()

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Индекс должен быть уникальным и возрастающим, а данные совпадать."""
        checks.unique_increasing_index(df_new)
        checks.df_data(self._df, df_new)

    def _new_events(self, event: events.TradingDayEnded) -> List[domain.AbstractEvent]:
        """Обновление индекса инфляции не порождает события."""
        return []
