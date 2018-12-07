"""Асинхронный клиент для доступа к данным."""
import contextlib

import aiomoex

from poptimizer import config
from poptimizer.storage import manager, store

# Максимальный размер хранилища данных и количество вложенных баз
MAX_SIZE = 10 * 2 ** 20
MAX_DBS = 2


class Client(contextlib.AbstractAsyncContextManager):
    """Асинхронный клиент для доступа к данным.

    Открывает соединение базой данных и интернетом, которые в последствии должны быть закрыты.
    Для удобства реализует протокол асинхронного контекстного менеджера.

    Атрибутами клиента являются менеджеры отдельных категорий данных. Так же можно обращаться к
    менеджерам напрямую внутри контекста, созданного клиентом.
    """

    def __init__(self):
        self._session = aiomoex.ISSClientSession()
        self._store = store.DataStore(config.DATA_PATH, MAX_SIZE, MAX_DBS)
        manager.AbstractManager.ISS_SESSION = self._session
        manager.AbstractManager.STORE = self._store

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._session.close()
        self._store.close()

    def __getattr__(self, item):
        sub_classes = manager.AbstractManager.__subclasses__()
        data_types = {str(cls.__name__).lower(): cls for cls in sub_classes}
        if item in data_types:
            return data_types[item]
        raise AttributeError
