"""Асинхронный клиент для доступа к данным."""
import contextlib

import aiomoex

from poptimizer import config
from poptimizer.store import manager, lmbd, moex, dividends, cpi

# Максимальный размер хранилища данных и количество вложенных баз
MAX_SIZE = 20 * 2 ** 20
MAX_DBS = 2


class Client(contextlib.AbstractAsyncContextManager):
    """Асинхронный клиент для доступа к данным.

    Открывает соединение базой данных и интернетом с использованием протокола асинхронного контекстного
    менеджера.

    Атрибутами клиента являются менеджеры отдельных категорий данных. Так же можно обращаться к
    менеджерам напрямую внутри контекста, созданного клиентом.
    """

    def __init__(self):
        self._session = aiomoex.ISSClientSession()
        self._store = lmbd.DataStore(config.DATA_PATH, MAX_SIZE, MAX_DBS)

    async def __aenter__(self):
        manager.AbstractManager.ISS_SESSION = self._session
        manager.AbstractManager.STORE = self._store
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._session.__aexit__(exc_type, exc_val, exc_tb)
        self._store.__exit__(exc_type, exc_val, exc_tb)

    securities = moex.Securities

    quotes = moex.Quotes

    index = moex.Index

    dividends = dividends.Dividends

    cpi = cpi.CPI
