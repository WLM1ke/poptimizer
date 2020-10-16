"""Загрузка данных с MOEX."""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

import aiohttp
import aiomoex
import pandas as pd
from pytz import timezone

from poptimizer.data.adapters import logger
from poptimizer.data.config import resources
from poptimizer.data.ports import col, outer

# Часовой пояс MOEX
MOEX_TZ = timezone("Europe/Moscow")
# Наименование столбцов в загружаемых котировках
OCHLV_COL = ("begin", "open", "close", "high", "low", "value")


class SecuritiesLoader(logger.LoaderLoggerMixin, outer.AbstractLoader):
    """Информация о всех торгующихся акциях."""

    def __init__(self) -> None:
        """Кэшируются данные, чтобы сократить количество обращений к серверу MOEX."""
        super().__init__()
        self._securities_cache: Optional[pd.DataFrame] = None
        self._cache_lock = asyncio.Lock()

    async def get(self, table_name: outer.TableName) -> pd.DataFrame:
        """Получение списка торгуемых акций с ISIN и размером лота."""
        name = self._log_and_validate_group(table_name, outer.SECURITIES)
        if name != outer.SECURITIES:
            raise outer.DataError(f"Некорректное имя таблицы для обновления {table_name}")

        async with self._cache_lock:
            if self._securities_cache is not None:
                self._logger.log(f"Загрузка из кэша {table_name}")
                return self._securities_cache

            columns = ("SECID", "ISIN", "LOTSIZE")
            http_session = resources.get_aiohttp_session()
            json = await aiomoex.get_board_securities(http_session, columns=columns)
            df = pd.DataFrame(json)
            df.columns = [col.TICKER, col.ISIN, col.LOT_SIZE]
            self._securities_cache = df.set_index(col.TICKER)

            return self._securities_cache


class IndexLoader(logger.LoaderLoggerMixin, outer.AbstractIncrementalLoader):
    """Котировки индекса полной доходности с учетом российских налогов - MCFTRR."""

    async def get(
        self,
        table_name: outer.TableName,
        last_index: Optional[str] = None,
    ) -> pd.DataFrame:
        """Получение цен закрытия индекса MCFTRR."""
        name = self._log_and_validate_group(table_name, outer.INDEX)
        if name != outer.INDEX:
            raise outer.DataError(f"Некорректное имя таблицы для обновления {table_name}")
        http_session = resources.get_aiohttp_session()
        json = await aiomoex.get_board_history(
            session=http_session,
            start=last_index,
            security=outer.INDEX,
            columns=("TRADEDATE", "CLOSE"),
            board="RTSI",
            market="index",
        )
        df = pd.DataFrame(json)
        df.columns = [col.DATE, col.CLOSE]
        df[col.DATE] = pd.to_datetime(df[col.DATE])
        return df.set_index(col.DATE)


def _previous_day_in_moscow() -> str:
    """Предыдущий день в Москве.

    Необходим для ограничения скачивания промежуточных свечек в последний день.
    """
    date = datetime.now(MOEX_TZ)
    date += timedelta(days=-1)
    return str(date.date())


async def _find_aliases(http_session: aiohttp.ClientSession, isin: str) -> List[str]:
    """Ищет все тикеры с эквивалентным регистрационным номером."""
    json = await aiomoex.find_securities(http_session, isin, columns=("secid", "isin"))
    return [row["secid"] for row in json if row["isin"] == isin]


async def _download_many(http_session: aiohttp.ClientSession, aliases: List[str]) -> pd.DataFrame:
    """Загрузка нескольких рядов котировок.

    Если пересекаются по времени, то берется ряд с максимальным оборотом.
    """
    json_all_aliases = []
    for ticker in aliases:
        json = await aiomoex.get_market_candles(http_session, ticker, end=_previous_day_in_moscow())
        json_all_aliases.extend(json)

    df = pd.DataFrame(columns=OCHLV_COL)
    if json_all_aliases:
        df = df.append(json_all_aliases)
        df = df.sort_values(by=["begin", "value"])
    return df.groupby("begin", as_index=False).last()


class QuotesLoader(logger.LoaderLoggerMixin, outer.AbstractIncrementalLoader):
    """Котировки акций."""

    def __init__(self, securities_loader: SecuritiesLoader) -> None:
        """Для загрузки нужны данные о регистрационных номерах."""
        super().__init__()
        self._securities_loader = securities_loader

    async def get(
        self,
        table_name: outer.TableName,
        last_index: Optional[str] = None,
    ) -> pd.DataFrame:
        """Получение котировок акций в формате OCHLV."""
        ticker = self._log_and_validate_group(table_name, outer.QUOTES)

        http_session = resources.get_aiohttp_session()
        if last_index is None:
            df = await self._first_load(http_session, ticker)
        else:
            json = await aiomoex.get_market_candles(
                http_session,
                ticker,
                start=last_index,
                end=_previous_day_in_moscow(),
            )
            df = pd.DataFrame(columns=OCHLV_COL)
            if json:
                df = pd.DataFrame(json)

        df = df[list(OCHLV_COL)]
        df.columns = [
            col.DATE,
            col.OPEN,
            col.CLOSE,
            col.HIGH,
            col.LOW,
            col.TURNOVER,
        ]
        df[col.DATE] = pd.to_datetime(df[col.DATE])
        return df.set_index(col.DATE)

    async def _first_load(self, http_session: aiohttp.ClientSession, ticker: str) -> pd.DataFrame:
        """Первая загрузка - поиск старых тикеров по ISIN и объединение рядов."""
        table_name = outer.TableName(outer.SECURITIES, outer.SECURITIES)
        df = await self._securities_loader.get(table_name)
        reg_num = df.at[ticker, col.ISIN]
        aliases = await _find_aliases(http_session, reg_num)
        return await _download_many(http_session, aliases)
