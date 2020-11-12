"""Таблица с индексом потребительской инфляции."""
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
        """После окончания торгового дня можно проверять наличие новых данных по инфляции."""
        return True

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
