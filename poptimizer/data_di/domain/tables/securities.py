"""Таблица с торгуемыми бумагами."""
from typing import ClassVar, Final, List

import pandas as pd

from poptimizer.data_di.adapters.gateways import moex
from poptimizer.data_di.domain import events
from poptimizer.data_di.domain.tables import base, checks
from poptimizer.shared import domain
from poptimizer.shared import col


class Securities(base.AbstractTable[events.TradingDayEnded]):
    """Таблица с данными о торгуемых бумагах.

    Обрабатывает событие об окончании торгов в режиме TQBR.
    Инициирует события о торговле конкретными бумагами.
    """

    group: ClassVar[base.GroupName] = base.SECURITIES
    _gateway: Final = moex.SecuritiesGateway()

    def _update_cond(self, event: events.TradingDayEnded) -> bool:
        """Если торговый день окончился, то обязательно требуется обновление."""
        return True

    async def _prepare_df(self, event: events.TradingDayEnded) -> pd.DataFrame:
        """Загружает новый DataFrame."""
        return await self._gateway.get()

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Индекс должен быть уникальным и возрастающим."""
        checks.unique_increasing_index(df_new)

    def _new_events(self, event: events.TradingDayEnded) -> List[domain.AbstractEvent]:
        """События факта торговли конкретных бумаг."""
        if (df := self._df) is None:
            raise base.TableNeverUpdatedError(self._id)

        trading_date = event.date

        return [
            events.TickerTraded(
                ticker,
                df.at[ticker, col.ISIN],
                trading_date,
            )
            for ticker in df.index
        ]
