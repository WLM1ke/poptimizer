"""Менеджеры данных для котировок и перечня торгуемых бумаг с MOEX."""
import asyncio
import functools
from typing import Tuple

import aiomoex
import pandas as pd

from poptimizer.store.manager import AbstractManager

# noinspection PyProtectedMember
from poptimizer.store.utils import TICKER, REG_NUMBER, LOT_SIZE, DATE, CLOSE, TURNOVER

# Данные об акциях хранятся в основной базе
NAME_SECURITIES = "securities"

# Данные по котировкам хранятся во вложенной базе
CATEGORY_QUOTES = "quotes"

# Функции для переобразования типов
FUNC_UNSIGNED = functools.partial(pd.to_numeric, downcast="unsigned")
FUNC_FLOAT = functools.partial(pd.to_numeric, downcast="float")
FUNC_DATE = functools.partial(pd.to_datetime, yearfirst=True, format="%Y-%m-%d")


class Securities(AbstractManager):
    """Информация о всех торгующихся акциях.

    При появлении новой информации создается с нуля, так как перечень торгуемых акций может как
    расширяться, так и сокращаться, а характеристики отдельных акций (например, размер лота) меняться
    со временем
    """

    CREATE_FROM_SCRATCH = True

    def __init__(self):
        super().__init__(NAME_SECURITIES)

    async def _download(self, name: str):
        columns = ("SECID", "REGNUMBER", "LOTSIZE")
        data = await aiomoex.get_board_securities(columns=columns)
        df = pd.DataFrame(data)[list(columns)]
        df.columns = [TICKER, REG_NUMBER, LOT_SIZE]
        df = df.set_index(TICKER)
        df.loc[:, LOT_SIZE] = df[LOT_SIZE].apply(FUNC_UNSIGNED)
        return df


class Quotes(AbstractManager):
    """Информация о котировках.

    Если у акции менялся тикер, но сохранялся регистрационный номер, то собирается полная история
    котировок для всех тикеров.
    """

    def __init__(self, tickers: Tuple[str, ...]):
        super().__init__(tickers, CATEGORY_QUOTES)

    async def _download(self, name: str):
        """Загружает полностью или только обновление по ценам закрытия и оборотам в рублях."""
        if self._data[name] is None:
            return await self._download_all(name)
        return await self._download_update(name)

    async def _download_all(self, name):
        """Загружает данные с учетом всех старых тикеров и изменения режима торгов."""
        aliases = await self._find_aliases(name)
        aws = [self._download_one_ticker(ticker) for ticker in aliases]
        dfs = await asyncio.gather(*aws)
        df = pd.concat(dfs, axis=0)
        df = self._clean_df(df)
        return df.sort_index()

    @staticmethod
    async def _find_aliases(ticker):
        """Ищет все тикеры с эквивалентным регистрационным номером."""
        securities = await Securities().get()
        number = securities.at[ticker, REG_NUMBER]
        results = await aiomoex.find_securities(number)
        return [result["secid"] for result in results if result["regnumber"] == number]

    async def _download_one_ticker(self, ticker):
        """Загружает котировки для одного тикера во всех режимах торгов."""
        data = await aiomoex.get_market_candles(ticker, end=self._last_history_date)
        return pd.DataFrame(data)

    @staticmethod
    def _clean_df(df):
        """Оставляет столбцы с ценами закрытия и объемами торгов, сортирует и приводит к корректному
        формату."""
        if not df.empty:
            df = df.loc[:, ["begin", "close", "value"]]
        else:
            df = df.reindex(columns=["begin", "close", "value"])
        df.columns = [DATE, CLOSE, TURNOVER]
        df.loc[:, DATE] = df[DATE].apply(FUNC_DATE)
        df.loc[:, CLOSE] = df[CLOSE].apply(FUNC_FLOAT)
        df.loc[:, TURNOVER] = df[TURNOVER].apply(FUNC_FLOAT)
        df = df.set_index(DATE)
        # Для старых котировок иногда бывали параллельны торги для нескольких тикеров одной бумаги
        if df.index.is_unique:
            return df
        # Для таких случаев выбираем торги с большим оборотом
        df.reset_index(inplace=True)
        df = df.loc[df.groupby(DATE)[TURNOVER].idxmax()]
        return df.set_index(DATE)

    async def _download_update(self, name):
        """Загружает данные с последнего имеющегося значения до конца истории."""
        old_df = self._data[name].value
        if old_df.empty:
            start = None
        else:
            start = str(old_df.index[-1].date())
        data = await aiomoex.get_market_candles(
            name, start=start, end=self._last_history_date
        )
        df = pd.DataFrame(data)
        return self._clean_df(df)
