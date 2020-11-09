"""Таблицы с индексами MOEX."""
from typing import ClassVar, Final, List

import pandas as pd

from poptimizer.data_di.adapters.gateways import moex
from poptimizer.data_di.domain import events
from poptimizer.data_di.domain.tables import base, checks
from poptimizer.data_di.shared import domain


class Indexes(base.AbstractTable[events.IndexCalculated]):
    """Таблица с индексами на закрытие торгового дня."""

    group: ClassVar[base.GroupName] = "quotes"
    _gateway: Final = moex.IndexesGateway()

    def _update_cond(self, event: events.IndexCalculated) -> bool:
        """Если торговый день окончился, то обязательно требуется обновление."""
        return True

    async def _prepare_df(self, event: events.IndexCalculated) -> pd.DataFrame:
        """Загружает новый DataFrame."""
        start_date = None
        if (df := self._df) is not None:
            start_date = str(df.index[-1].date())

        last_date = str(event.date)

        df_new = self._gateway.get(event.ticker, start_date, last_date)

        if df is None:
            return df_new

        return pd.concat([df.iloc[:-1], df_new], axis=0)

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Индекс должен быть уникальным и возрастающим, а данные совпадать."""
        checks.unique_increasing_index(df_new)
        checks.df_data(self._df, df_new)

    def _new_events(self, event: events.IndexCalculated) -> List[domain.AbstractEvent]:
        """Обновление индекса не порождает события."""
        return []
