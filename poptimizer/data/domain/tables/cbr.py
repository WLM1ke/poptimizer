"""Таблица с максимальными ставками по депозитам в крупнейших банках."""
from typing import ClassVar, Final, List, cast

import pandas as pd

from poptimizer.data import ports
from poptimizer.data.adapters.gateways import cbr
from poptimizer.data.domain import events
from poptimizer.data.domain.tables import base
from poptimizer.shared import domain


class RF(base.AbstractTable[events.TradingDayEnded]):
    """Таблица с максимальными ставками по депозитам в крупнейших банках.

    Используется в качестве безрисковой ставки для частного российского инвестора.
    """

    group: ClassVar[ports.GroupName] = ports.RF
    _gateway: Final = cbr.RFGateway()

    def _update_cond(self, event: events.TradingDayEnded) -> bool:
        """Данные публикуются раз в декаду — обновлять имеет смысл через 10 дней."""
        if (df := self._df) is None:
            return True

        next_update = df.index[-1] + pd.DateOffset(days=10)
        next_update = next_update.date()

        return cast(bool, next_update <= event.date)

    async def _prepare_df(self, event: events.TradingDayEnded) -> pd.DataFrame:
        """Загружает новый DataFrame."""
        return await self._gateway()

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Индекс должен быть уникальным и возрастающим."""
        base.check_unique_increasing_index(df_new)

    def _new_events(self, event: events.TradingDayEnded) -> List[domain.AbstractEvent]:
        """Обновление индекса инфляции не порождает события."""
        return []
