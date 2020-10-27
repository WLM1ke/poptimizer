"""Загрузка таблицы с диапазоном торговых дат."""
import aiohttp
import aiomoex
import pandas as pd
from injector import Inject

from poptimizer.data_di.adapters.logger import AsyncLogger
from poptimizer.data_di.ports import gateways


class TradingDatesGateway(gateways.AbstractGateway):
    """Обновление для таблиц с диапазоном доступных торговых дат."""

    def __init__(self, session: Inject[aiohttp.ClientSession], logger: Inject[AsyncLogger]) -> None:
        """Кэшируются данные, чтобы сократить количество обращений к серверу MOEX."""
        self._logger = logger
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
