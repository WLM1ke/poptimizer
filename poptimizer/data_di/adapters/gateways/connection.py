"""Фабрика для асинхронного http-соединения."""
import abc
import asyncio
import atexit
from typing import Final

import aiohttp
import pandas as pd

# Размер пула http-соединений - при большем размере многие сайты ругаются
_POOL_SIZE = 20


def _clean_up(session: aiohttp.ClientSession) -> None:
    """Закрывает клиентскую сессию aiohttp."""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(session.close())


def _session_factory(pool_size: int) -> aiohttp.ClientSession:
    """Клиентская сессия aiohttp."""
    connector = aiohttp.TCPConnector(limit=pool_size)
    session = aiohttp.ClientSession(connector=connector)
    atexit.register(_clean_up, session)
    return session


HTTP_SESSION: Final = _session_factory(_POOL_SIZE)


class BaseGateway:
    """Базовый шлюз."""

    def __init__(
        self,
        session: aiohttp.ClientSession = HTTP_SESSION,
    ) -> None:
        """Сохраняет http-сессию."""
        self._session = session


class DivGateway(BaseGateway):
    """Базовый шлюз."""

    @abc.abstractmethod
    async def get(self, ticker: str) -> pd.DataFrame:
        """Дивиденды для данного тикера."""
