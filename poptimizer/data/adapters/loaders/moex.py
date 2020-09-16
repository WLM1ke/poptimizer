"""Загрузка данных с MOEX."""
import asyncio
import datetime
from typing import List, Optional, cast

import aiohttp
import aiomoex
import pandas as pd
from pytz import timezone

from poptimizer.data.adapters import logger
from poptimizer.data.config import resources
from poptimizer.data.ports import col, outer

# Часовой пояс MOEX
MOEX_TZ = timezone("Europe/Moscow")


class SecuritiesLoader(logger.LoggerMixin, outer.AbstractLoader):
    """Информация о всех торгующихся акциях."""

    def __init__(self) -> None:
        """Кэшируются данные, чтобы сократить количество обращений к серверу MOEX."""
        super().__init__()
        self._securities_cache: Optional[pd.DataFrame] = None
        self._cache_lock = asyncio.Lock()

    async def get(self, table_name: outer.TableName) -> pd.DataFrame:
        """Получение списка торгуемых акций с регистрационным номером и размером лота."""
        name = self._log_and_validate_group(table_name, outer.SECURITIES)
        if name != outer.SECURITIES:
            raise outer.DataError(f"Некорректное имя таблицы для обновления {table_name}")

        async with self._cache_lock:
            if self._securities_cache is not None:
                self._logger.info(f"Загрузка из кэша {table_name}")
                return self._securities_cache

            columns = ("SECID", "REGNUMBER", "LOTSIZE")
            http_session = resources.get_aiohttp_session()
            json = await aiomoex.get_board_securities(http_session, columns=columns)
            df = pd.DataFrame(json)
            df.columns = [col.TICKER, col.REG_NUMBER, col.LOT_SIZE]
            self._securities_cache = df.set_index(col.TICKER)

            return self._securities_cache


class IndexLoader(logger.LoggerMixin, outer.AbstractIncrementalLoader):
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
    date = datetime.datetime.now(MOEX_TZ)
    date += datetime.timedelta(days=-1)
    return str(date.date())


async def _find_aliases(http_session: aiohttp.ClientSession, reg_num: str) -> List[str]:
    """Ищет все тикеры с эквивалентным регистрационным номером."""
    json = await aiomoex.find_securities(http_session, reg_num)
    return [row["secid"] for row in json if row["regnumber"] == reg_num]


async def _download_many(http_session: aiohttp.ClientSession, aliases: List[str]) -> pd.DataFrame:
    """Загрузка нескольких рядов котировок."""
    json_all_aliases = []
    for ticker in aliases:
        json = await aiomoex.get_market_candles(http_session, ticker, end=_previous_day_in_moscow())
        json_all_aliases.extend(json)

    df = pd.DataFrame(columns=["open", "close", "high", "low", "value", "volume", "begin", "end"])
    if json_all_aliases:
        df = df.append(json_all_aliases)
        df = df.sort_values(by=["begin", "value"])
    return df.groupby("begin", as_index=False).last()


class QuotesLoader(logger.LoggerMixin, outer.AbstractIncrementalLoader):
    """Котировки акций."""

    def __init__(self, securities_loader: SecuritiesLoader) -> None:
        """Для загрузки нужны данные регистрационных номерах."""
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
            reg_num = await self._get_reg_num(ticker)
            aliases = await _find_aliases(http_session, reg_num)
            df = await _download_many(http_session, aliases)
        else:
            json = await aiomoex.get_market_candles(
                http_session,
                ticker,
                start=last_index,
                end=_previous_day_in_moscow(),
            )
            df = pd.DataFrame(json)

        df = df[["begin", "open", "close", "high", "low", "value"]]
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

    async def _get_reg_num(self, ticker: str) -> str:
        """Регистрационный номер акции."""
        table_name = outer.TableName(outer.SECURITIES, outer.SECURITIES)
        df = await self._securities_loader.get(table_name)
        return cast(str, df.at[ticker, col.REG_NUMBER])
