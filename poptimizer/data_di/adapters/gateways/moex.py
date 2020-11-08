"""Загрузка различных данных с MOEX."""
from typing import List, Optional

import aiohttp
import aiomoex
import pandas as pd

from poptimizer.data_di.adapters.gateways import connection
from poptimizer.data_di.shared import adapters, col


class BaseGateway:
    """Базовый шлюз."""

    _logger = adapters.AsyncLogger()

    def __init__(
        self,
        session: aiohttp.ClientSession = connection.HTTP_SESSION,
    ) -> None:
        """Сохраняет http-сессию."""
        self._session = session


class TradingDatesGateway(BaseGateway):
    """Обновление для таблиц с диапазоном доступных торговых дат."""

    async def get(self) -> pd.DataFrame:
        """Получение обновленных данных о доступном диапазоне торговых дат."""
        self._logger("Загрузка данных по торговым дням")
        json = await aiomoex.get_board_dates(
            self._session,
            board="TQBR",
            market="shares",
            engine="stock",
        )
        return pd.DataFrame(json, dtype="datetime64[ns]")


class SecuritiesGateway(BaseGateway):
    """Информация о всех торгующихся акциях."""

    async def get(self) -> pd.DataFrame:
        """Получение списка торгуемых акций с ISIN и размером лота."""
        self._logger("Загрузка данных по торгуемым бумагам")

        columns = ("SECID", "ISIN", "LOTSIZE")
        json = await aiomoex.get_board_securities(self._session, columns=columns)
        df = pd.DataFrame(json)
        df.columns = [col.TICKER, col.ISIN, col.LOT_SIZE]
        return df.set_index(col.TICKER)


class AliasesGateway(BaseGateway):
    """Ищет все тикеры с эквивалентным регистрационным номером."""

    async def get(self, isin: str) -> List[str]:
        """Ищет все тикеры с эквивалентным ISIN."""
        json = await aiomoex.find_securities(self._session, isin, columns=("secid", "isin"))
        return [row["secid"] for row in json if row["isin"] == isin]


class QuotesGateway(BaseGateway):
    """Загружает котировки акций."""

    async def get(
        self,
        ticker: str,
        last_date: str,
        start_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Получение котировок акций в формате OCHLV."""
        json = await aiomoex.get_market_candles(
            self._session,
            ticker,
            start=start_date,
            end=last_date,
        )
        df = pd.DataFrame(columns=("begin", "open", "close", "high", "low", "value"))
        if json:
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
