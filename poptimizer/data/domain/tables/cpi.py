"""Таблица с индексом потребительской инфляции."""
from datetime import timedelta
from typing import ClassVar, Final, List, cast

import pandas as pd

from poptimizer.data import ports
from poptimizer.data.adapters.gateways import cpi
from poptimizer.data.domain import events
from poptimizer.data.domain.tables import base
from poptimizer.shared import domain


class CPI(base.AbstractTable[events.TradingDayEnded]):
    """Таблица с потребительской инфляцией."""

    group: ClassVar[ports.GroupName] = ports.CPI
    _gateway: Final = cpi.CPIGateway()

    def _update_cond(self, event: events.TradingDayEnded) -> bool:
        """Инфляция обновляется при отсутствии или окончании очередного месяца."""
        if (df := self._df) is None:
            return True

        last_cpi_month = df.index[-1].month
        last_full_month = (event.date.replace(day=1) - timedelta(days=1)).month

        return cast(bool, last_cpi_month != last_full_month)

    async def _prepare_df(self, event: events.TradingDayEnded) -> pd.DataFrame:
        """Загружает новый DataFrame."""
        return await self._gateway()

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Индекс должен быть уникальным и возрастающим, а данные совпадать."""
        base.check_unique_increasing_index(df_new)
        base.check_dfs_mismatch(self.id_, self._df, df_new)

    def _new_events(self, event: events.TradingDayEnded) -> List[domain.AbstractEvent]:
        """Обновление индекса инфляции не порождает события."""
        return []
