"""Таблицы с котировками."""
import asyncio
from typing import ClassVar, Final, List

import pandas as pd

from poptimizer.data_di.adapters.gateways import moex
from poptimizer.data_di.domain import events
from poptimizer.data_di.domain.tables import base
from poptimizer.data_di.shared import col, domain


class Quotes(base.AbstractTable[events.TickerTraded]):
    """Таблица с котировками в формате в формате OCHLV.

    При создании загружаются данные по всем бумагам с одинаковым ISIN.
    При обновлении добавляются только данные актуального тикера.
    """

    group: ClassVar[base.GroupName] = "quotes"
    _aliases: Final = moex.AliasesGateway()
    _quotes: Final = moex.QuotesGateway()

    def _update_cond(self, event: events.TickerTraded) -> bool:
        """Если торговый день окончился, то обязательно требуется обновление."""
        return True

    async def _prepare_df(self, event: events.TickerTraded) -> pd.DataFrame:
        """Загружает новый DataFrame."""
        tickers = [event.ticker]
        start_date = None

        if self._df is None:
            tickers = await self._aliases.get(event.isin)
        else:
            start_date = str(self._df.index[-1].date())

        last_date = str(event.date)

        coro = [await self._quotes.get(ticker, start_date, last_date) for ticker in tickers]
        df = pd.concat(await asyncio.gather(*coro), axis=0)

        if len(tickers) > 1:
            df = df.sort_values(by=[col.DATE, col.TURNOVER])
            df = df.groupby(col.DATE).last()

        if self._df is None:
            return df

        return pd.concat([self._df.iloc[:-1], df], axis=0)

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Индекс должен быть уникальным и возрастающим."""
        base.check_unique_increasing_index(df_new)
        if (df_old := self._df) is None:
            return

        df_new_val = df_new.reindex(df_old.index)
        try:
            pd.testing.assert_frame_equal(df_new_val, df_old)
        except AssertionError:
            raise base.TableNewDataMismatchError()

    def _new_events(self, event: events.TickerTraded) -> List[domain.AbstractEvent]:
        """Обновление котировок не порождает события."""
        return []
