"""Таблицы с котировками."""
import asyncio
from typing import ClassVar, Final, List

import pandas as pd

from poptimizer.data_di import ports
from poptimizer.data_di.adapters.gateways import moex
from poptimizer.data_di.domain import events
from poptimizer.data_di.domain.tables import base
from poptimizer.shared import col, domain


class Quotes(base.AbstractTable[events.TickerTraded]):
    """Таблица с котировками в формате в формате OCHLV.

    При создании загружаются данные по всем бумагам с одинаковым ISIN.
    При обновлении добавляются только данные актуального тикера.
    """

    group: ClassVar[ports.GroupName] = ports.QUOTES
    _aliases: Final = moex.AliasesGateway()
    _quotes: Final = moex.QuotesGateway()

    def _update_cond(self, event: events.TickerTraded) -> bool:
        """Если торговый день окончился, то обязательно требуется обновление."""
        return True

    async def _prepare_df(self, event: events.TickerTraded) -> pd.DataFrame:
        """Готовится новый DataFrame.

        Для новых тикеров и параллельных торгов выбирается тикер с максимальным объемом.

        Если новые данные пустые (бывает для давно не торгующейся бумаги, которая раньше
        торговалась под другим тикером), то возвращаются старые данные.

        При наличие старых и новых данных, они склеиваются.
        """
        df_new = await self._load_df(event)

        if (df := self._df) is None:
            df_new = df_new.sort_values(by=[col.DATE, col.TURNOVER])
            return df_new.groupby(col.DATE).last()

        if df_new.empty:
            return df

        return pd.concat([df.iloc[:-1], df_new], axis=0)

    async def _load_df(self, event: events.TickerTraded) -> pd.DataFrame:
        """Загружает данные для обновления.

        Если данные отсутствуют, то загружается информация для всех тикеров таким же ISIN.

        Для не пустых старых данных загрузка ведется с последней присутствующей даты.
        """
        tickers = [event.ticker]
        start_date = None

        if (df := self._df) is None:
            tickers = await self._aliases.get(event.isin)
        elif not df.empty:
            start_date = str(df.index[-1].date())

        last_date = str(event.date)

        aws = [self._quotes.get(ticker, event.market, start_date, last_date) for ticker in tickers]

        return pd.concat(
            await asyncio.gather(*aws),
            axis=0,
        )

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Индекс должен быть уникальным и возрастающим, а данные стыковаться."""
        base.check_unique_increasing_index(df_new)
        base.check_dfs_mismatch(self.id_, self._df, df_new)

    def _new_events(self, event: events.TickerTraded) -> List[domain.AbstractEvent]:
        """Обновление котировок не порождает события."""
        return []
