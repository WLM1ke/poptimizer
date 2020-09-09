"""Загрузка данных с MOEX."""
import datetime
import threading
from typing import List, Optional, cast

import aiomoex
import apimoex
import pandas as pd
from pytz import timezone

from poptimizer.data.adapters import logger
from poptimizer.data.config import resources
from poptimizer.data.ports import base, col

# Часовой пояс MOEX
MOEX_TZ = timezone("Europe/Moscow")


class SecuritiesLoader(logger.LoggerMixin, base.AbstractLoader):
    """Информация о всех торгующихся акциях."""

    def __init__(self) -> None:
        """Кэшируются данные, чтобы сократить количество обращений к серверу MOEX."""
        super().__init__()
        self._securities_cache: Optional[pd.DataFrame] = None
        self._cache_lock = threading.RLock()

    async def get(self, table_name: base.TableName) -> pd.DataFrame:
        """Получение списка торгуемых акций с регистрационным номером и размером лота."""
        name = self._log_and_validate_group(table_name, base.SECURITIES)
        if name != base.SECURITIES:
            raise base.DataError(f"Некорректное имя таблицы для обновления {table_name}")

        with self._cache_lock:
            if self._securities_cache is not None:
                self._logger.info(f"Загрузка из кэша {table_name}")
                return self._securities_cache

            columns = ("SECID", "REGNUMBER", "LOTSIZE")
            json = await aiomoex.get_board_securities(resources.get_aiohttp_session(), columns=columns)
            df = pd.DataFrame(json)
            df.columns = [col.TICKER, col.REG_NUMBER, col.LOT_SIZE]
            self._securities_cache = df.set_index(col.TICKER)

            return self._securities_cache


class IndexLoader(logger.LoggerMixin, base.AbstractIncrementalLoader):
    """Котировки индекса полной доходности с учетом российских налогов - MCFTRR."""

    async def get(
        self,
        table_name: base.TableName,
        start_date: Optional[datetime.date] = None,
    ) -> pd.DataFrame:
        """Получение цен закрытия индекса MCFTRR."""
        name = self._log_and_validate_group(table_name, base.INDEX)
        if name != base.INDEX:
            raise base.DataError(f"Некорректное имя таблицы для обновления {table_name}")

        json = apimoex.get_board_history(
            session=resources.get_http_session(),
            start=str(start_date),
            security=base.INDEX,
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


def _find_aliases(reg_num: str) -> List[str]:
    """Ищет все тикеры с эквивалентным регистрационным номером."""
    json = apimoex.find_securities(resources.get_http_session(), reg_num)
    return [row["secid"] for row in json if row["regnumber"] == reg_num]


def _download_many(aliases: List[str]) -> pd.DataFrame:
    """Загрузка нескольких рядов котировок."""
    http_session = resources.get_http_session()
    json_all_aliases = []
    for ticker in aliases:
        json = apimoex.get_market_candles(http_session, ticker, end=_previous_day_in_moscow())
        json_all_aliases.extend(json)

    df = pd.DataFrame(columns=["begin", "open", "close", "high", "low", "value"])
    if json_all_aliases:
        df = pd.DataFrame(json_all_aliases)
        df = df.sort_values(by=["begin", "value"])
    return df.groupby("begin", as_index=False).last()


class QuotesLoader(logger.LoggerMixin, base.AbstractIncrementalLoader):
    """Котировки акций."""

    def __init__(self, securities_loader: SecuritiesLoader) -> None:
        """Для загрузки нужны данные регистрационных номерах."""
        super().__init__()
        self._securities_loader = securities_loader

    async def get(
        self,
        table_name: base.TableName,
        start_date: Optional[datetime.date] = None,
    ) -> pd.DataFrame:
        """Получение котировок акций в формате OCHLV."""
        ticker = self._log_and_validate_group(table_name, base.QUOTES)

        if start_date is None:
            reg_num = await self._get_reg_num(ticker)
            aliases = _find_aliases(reg_num)
            df = _download_many(aliases)
        else:
            json = apimoex.get_market_candles(
                resources.get_http_session(),
                ticker,
                start=str(start_date),
                end=_previous_day_in_moscow(),
            )
            df = pd.DataFrame(json)

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
        table_name = base.TableName(base.SECURITIES, base.SECURITIES)
        df = await self._securities_loader.get(table_name)
        return cast(str, df.at[ticker, col.REG_NUMBER])
