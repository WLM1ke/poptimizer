"""Таблицы с дивидендами."""
from typing import ClassVar, Final, List

import pandas as pd

from poptimizer.data_di.adapters.gateways import dividends, smart_lab
from poptimizer.data_di.domain import events
from poptimizer.data_di.domain.tables import base, checks
from poptimizer.data_di.shared import col, domain


class Dividends(base.AbstractTable[events.TickerTraded]):
    """Таблица с основной версией дивидендов."""

    group: ClassVar[base.GroupName] = base.DIVIDENDS
    _gateway: Final = dividends.DividendsGateway()

    def _update_cond(self, event: events.TickerTraded) -> bool:
        """Если дивиденды отсутствуют, то их надо загрузить."""
        return self._df is None

    async def _prepare_df(self, event: events.TickerTraded) -> pd.DataFrame:
        """Загружает новый DataFrame полностью."""
        return await self._gateway.get(event.ticker)

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Индекс должен быть уникальным и возрастающим."""
        checks.unique_increasing_index(df_new)

    def _new_events(self, event: events.TickerTraded) -> List[domain.AbstractEvent]:
        """Обновление дивидендов не порождает события."""
        return []


class SmartLab(base.AbstractTable[events.TradingDayEnded]):
    """Таблица с ожидаемыми дивидендами со https://www.smart-lab.ru.

    Создает события с новыми дивидендами.
    """

    group: ClassVar[base.GroupName] = base.SMART_LAB
    _gateway: Final = smart_lab.SmartLabGateway()

    def _update_cond(self, event: events.TradingDayEnded) -> bool:
        """Если торговый день окончился, всегда обновление."""
        return True

    async def _prepare_df(self, event: events.TradingDayEnded) -> pd.DataFrame:
        """Загружает новый DataFrame полностью."""
        return await self._gateway.get()

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Нет проверок."""

    def _new_events(self, event: events.TradingDayEnded) -> List[domain.AbstractEvent]:
        """Создает события о новых дивидендах."""
        if (df := self._df) is None:
            raise base.TableNeverUpdatedError(self._id)

        div_tickers = set(df.index)
        new_events: List[domain.AbstractEvent] = []

        for ticker in div_tickers:
            df_div = df[df == ticker]
            df_div = df_div.set_index(col.DATE)
            df_div = df_div[[col.DIVIDENDS]]
            df_div.columns = ["SmartLab"]
            new_events.append(events.DivExpected(ticker, df_div))

        return new_events
