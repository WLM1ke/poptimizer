"""Загрузка таблицы с диапазоном торговых дат."""
import aiohttp
import aiomoex
import pandas as pd

from poptimizer.data_di.adapters import connection
from poptimizer.data_di.shared import adapters


class TradingDatesGateway:
    """Обновление для таблиц с диапазоном доступных торговых дат."""

    _logger = adapters.AsyncLogger()

    def __init__(
        self,
        session: aiohttp.ClientSession = connection.HTTP_SESSION,
    ) -> None:
        """Сохраняет http-сессию."""
        self._session = session

    async def get(self) -> pd.DataFrame:
        """Получение обновленных данных о доступном диапазоне торговых дат."""
        self._logger.log("Загрузка данных по торговым дням")
        json = await aiomoex.get_board_dates(
            self._session,
            board="TQBR",
            market="shares",
            engine="stock",
        )
        return pd.DataFrame(json, dtype="datetime64[ns]")
