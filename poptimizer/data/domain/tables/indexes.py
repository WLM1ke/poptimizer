"""Таблицы с индексами MOEX."""
from typing import ClassVar, Final, List

import pandas as pd

from poptimizer.data import ports
from poptimizer.data.adapters.gateways import moex
from poptimizer.data.domain import events
from poptimizer.data.domain.tables import base
from poptimizer.shared import domain


class Indexes(base.AbstractTable[events.IndexCalculated]):
    """Таблица с индексами на закрытие торгового дня."""

    group: ClassVar[ports.GroupName] = ports.INDEX
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

        df_new = await self._gateway(event.ticker, start_date, last_date)

        if df is None:
            return df_new

        return pd.concat([df.iloc[:-1], df_new], axis=0)

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Индекс должен быть уникальным и возрастающим, а данные совпадать."""
        base.check_unique_increasing_index(df_new)
        base.check_dfs_mismatch(self.id_, self._df, df_new)

    def _new_events(self, event: events.IndexCalculated) -> List[domain.AbstractEvent]:
        """Обновление индекса не порождает события."""
        return []
