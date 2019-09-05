"""Асинхронный клиент для доступа к данным."""
import contextlib

import aiomoex

from poptimizer import config
from poptimizer.store import manager, lmbd, moex, dividends, smart_lab, dohod, conomy

# Максимальный размер хранилища данных и количество вложенных баз
MAX_SIZE = 20 * 2 ** 20
MAX_DBS = 3


def open_store():
    """Открывает key-value хранилище."""
    return lmbd.DataStore(config.DATA_PATH, MAX_SIZE, MAX_DBS)


class Client(contextlib.AbstractAsyncContextManager):
    """Асинхронный клиент для доступа к данным.

    Открывает соединение базой данных и интернетом с использованием протокола асинхронного контекстного
    менеджера.

    Атрибутами клиента являются менеджеры отдельных категорий данных. Так же можно обращаться к
    менеджерам напрямую внутри контекста, созданного клиентом.
    """

    def __init__(self):
        self._session = aiomoex.ISSClientSession()
        self._store = open_store()

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

    smart_lab = smart_lab.SmartLab

    dohod = dohod.Dohod

    conomy = conomy.Conomy
