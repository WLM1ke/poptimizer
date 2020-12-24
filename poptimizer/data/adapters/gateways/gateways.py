"""Базовые классы шлюзов."""
import abc

import aiohttp
import pandas as pd

from poptimizer.shared import connections


class BaseGateway(abc.ABC):
    """Базовый шлюз."""

    def __init__(
        self,
        session: aiohttp.ClientSession = connections.HTTP_SESSION,
    ) -> None:
        """Сохраняет http-сессию."""
        self._session = session


class DivGateway(BaseGateway):
    """Базовый шлюз для дивидендов."""

    @abc.abstractmethod
    async def get(self, ticker: str) -> pd.DataFrame:
        """Дивиденды для данного тикера."""

    def _sort_and_agg(self, df: pd.DataFrame) -> pd.DataFrame:
        """Сортировка и агрегация по индексу."""
        df = df.sort_index(axis=0)
        return df.groupby(lambda date: date).sum()
