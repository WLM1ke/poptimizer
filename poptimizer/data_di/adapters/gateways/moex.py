"""Загрузка различных данных с MOEX."""
from typing import List, Optional

import aiomoex
import pandas as pd

from poptimizer.data_di.adapters.gateways import gateways
from poptimizer.shared import adapters, col


class TradingDatesGateway(gateways.BaseGateway):
    """Обновление для таблиц с диапазоном доступных торговых дат."""

    _logger = adapters.AsyncLogger()

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


class IndexesGateway(gateways.BaseGateway):
    """Котировки различных индексов на MOEX."""

    _logger = adapters.AsyncLogger()

    async def get(
        self,
        ticker: str,
        start_date: Optional[str],
        last_date: str,
    ) -> pd.DataFrame:
        """Получение значений индекса на закрытие для диапазона дат."""
        self._logger(f"{ticker}({start_date}, {last_date})")
        json = await aiomoex.get_market_history(
            session=self._session,
            start=start_date,
            end=last_date,
            security=ticker,
            columns=("TRADEDATE", "CLOSE"),
            market="index",
        )
        df = pd.DataFrame(json)
        df.columns = [col.DATE, col.CLOSE]
        df[col.DATE] = pd.to_datetime(df[col.DATE])
        return df.set_index(col.DATE)


class SecuritiesGateway(gateways.BaseGateway):
    """Информация о всех торгующихся акциях."""

    _logger = adapters.AsyncLogger()

    async def get(self, market: str, board: str) -> pd.DataFrame:
        """Получение списка торгуемых акций с ISIN и размером лота."""
        self._logger("Загрузка данных по торгуемым бумагам")

        columns = ("SECID", "ISIN", "LOTSIZE")
        json = await aiomoex.get_board_securities(
            self._session,
            market=market,
            board=board,
            columns=columns,
        )
        df = pd.DataFrame(json)
        df.columns = [col.TICKER, col.ISIN, col.LOT_SIZE]
        return df.set_index(col.TICKER)


class AliasesGateway(gateways.BaseGateway):
    """Ищет все тикеры с эквивалентным регистрационным номером."""

    _logger = adapters.AsyncLogger()

    async def get(self, isin: str) -> List[str]:
        """Ищет все тикеры с эквивалентным ISIN."""
        self._logger(isin)

        json = await aiomoex.find_securities(self._session, isin, columns=("secid", "isin"))
        return [row["secid"] for row in json if row["isin"] == isin]


class QuotesGateway(gateways.BaseGateway):
    """Загружает котировки акций."""

    _logger = adapters.AsyncLogger()

    async def get(
        self,
        ticker: str,
        market: str,
        start_date: Optional[str],
        last_date: str,
    ) -> pd.DataFrame:
        """Получение котировок акций в формате OCHLV."""
        self._logger(f"{ticker}({start_date}, {last_date})")

        json = await aiomoex.get_market_candles(
            self._session,
            ticker,
            market=market,
            start=start_date,
            end=last_date,
        )

        df = pd.DataFrame(columns=("begin", "open", "close", "high", "low", "value", "end", "volume"))
        df = df.append(json)
        df = df.drop(["end", "volume"], axis=1)

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
