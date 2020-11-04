"""Загрузка различных данных с MOEX."""
import aiohttp
import aiomoex
import pandas as pd

from poptimizer.data_di.adapters.gateways import connection
from poptimizer.data_di.shared import adapters, col


class TradingDatesGateway:
    """Обновление для таблиц с диапазоном доступных торговых дат."""

    _logger = adapters.AsyncLogger()

    def __init__(
        self,
        session: aiohttp.ClientSession = connection.HTTP_SESSION,
    ) -> None:
        """Сохраняет http-сессию."""
        self._session = session

    async def __call__(self) -> pd.DataFrame:
        """Получение обновленных данных о доступном диапазоне торговых дат."""
        self._logger("Загрузка данных по торговым дням")
        json = await aiomoex.get_board_dates(
            self._session,
            board="TQBR",
            market="shares",
            engine="stock",
        )
        return pd.DataFrame(json, dtype="datetime64[ns]")


class SecuritiesGateway:
    """Информация о всех торгующихся акциях."""

    _logger = adapters.AsyncLogger()

    def __init__(
        self,
        session: aiohttp.ClientSession = connection.HTTP_SESSION,
    ) -> None:
        """Сохраняет http-сессию."""
        self._session = session

    async def __call__(self) -> pd.DataFrame:
        """Получение списка торгуемых акций с ISIN и размером лота."""
        self._logger("Загрузка данных по торгуемым бумагам")

        columns = ("SECID", "ISIN", "LOTSIZE")
        json = await aiomoex.get_board_securities(self._session, columns=columns)
        df = pd.DataFrame(json)
        df.columns = [col.TICKER, col.ISIN, col.LOT_SIZE]
        return df.set_index(col.TICKER)
