"""Фабрика для асинхронного http-соединения."""
import abc

import aiohttp
import pandas as pd

from poptimizer.shared import connections


class BaseGateway:
    """Базовый шлюз."""

    def __init__(
        self,
        session: aiohttp.ClientSession = connections.HTTP_SESSION,
    ) -> None:
        """Сохраняет http-сессию."""
        self._session = session


class DivGateway(BaseGateway):
    """Базовый шлюз."""

    @abc.abstractmethod
    async def get(self, ticker: str) -> pd.DataFrame:
        """Дивиденды для данного тикера."""
