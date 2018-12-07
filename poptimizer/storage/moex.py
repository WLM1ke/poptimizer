"""Менеджеры данных с MOEX."""
import functools
from typing import Tuple

import aiomoex
import pandas as pd

from poptimizer.storage.manager import AbstractManager

# Данные об акциях хранятся в основной базе
NAME_SECURITIES = "securities"

# Данные по котировкам хранятся во вложенной базе
CATEGORY_QUOTES = "quotes"

# Функции для переобразования типов
FUNC_UNSIGNED = functools.partial(pd.to_numeric, downcast="unsigned")
FUNC_FLOAT = functools.partial(pd.to_numeric, downcast="float")
FUNC_DATE = functools.partial(pd.to_datetime, yearfirst=True, format="%Y-%m-%d")


class Securities(AbstractManager):
    """Информация о всех торгующихся акциях."""

    CREATE_FROM_SCRATCH = True

    def __init__(self):
        super().__init__(NAME_SECURITIES)

    async def _download(self, name: str):
        columns = ("SECID", "REGNUMBER", "LOTSIZE")
        data = await aiomoex.get_board_securities(columns=columns)
        df = pd.DataFrame(data)
        df = df.set_index("SECID")
        df.loc[:, "LOTSIZE"] = df["LOTSIZE"].apply(FUNC_UNSIGNED)
        return df


class Quotes(AbstractManager):
    """Информация о котировках.

    Если у акции менялся тикер, но сохранялся регистрационный номер, то собирается полная история
    котировок для всех тикеров.
    """

    def __init__(self, names: Tuple[str]):
        super().__init__(names, CATEGORY_QUOTES)

    async def _download(self, name: str):
        """Загружает полностью или обновление по ценам закрытия и оборотам в рублях."""
        if self._data[name] is None:
            return await self._download_all(name)
        return await self._download_update(name)

    async def _download_all(self, name):
        """Загружает данные с учетом всех старых тикеров и изменения режима торгов."""
        aliases = await self._find_aliases(name)
        aws = [self._download_one_ticker(ticker) for ticker in aliases]
        dfs = await asyncio.gather(*aws)
        df = pd.concat(dfs, axis=0)
        return self._clean_df(df)

    @staticmethod
    async def _find_aliases(ticker):
        """Ищет все тикеры с эквивалентным регистрационным номером."""
        securities = await Securities().get()
        number = securities.at[ticker, "REGNUMBER"]
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
        df = df.loc[:, ["begin", "close", "value"]]
        df.loc[:, "begin"] = df["begin"].apply(FUNC_DATE)
        df.loc[:, "close"] = df["close"].apply(FUNC_FLOAT)
        df.loc[:, "value"] = df["value"].apply(FUNC_FLOAT)
        df = df.set_index("begin")
        return df.sort_index()

    async def _download_update(self, name):
        """Загружает данные с последнего имеющегося значения до конца истории."""
        start = self._data[name].value.index[-1].date
        data = await aiomoex.get_board_candles(
            name, start=str(start), end=self._last_history_date
        )
        df = pd.DataFrame(data)
        return self._clean_df(df)


if __name__ == "__main__":
    from poptimizer.storage.client import Client
    import asyncio

    async def main():
        """qqq"""
        async with Client() as client:
            print(await client.quotes("UPRO").get())

    asyncio.run(main())
