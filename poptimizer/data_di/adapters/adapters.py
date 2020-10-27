"""Конфигурация внешней инфраструктуры."""
from typing import Final, Type

import aiohttp
import injector
from motor import motor_asyncio

from poptimizer.data_di.adapters import connection, logger, mapper

# Размер пула http-соединений - при большем размере многие сайты ругаются
POOL_SIZE: Final = 20

# Ссылка на локальный MongoDB сервер
MONGO_URI: Final = "mongodb://localhost:27017"


class Adapters(injector.Module):
    """Конфигурация внешней инфраструктуры."""

    def configure(self, binder: injector.Binder) -> None:
        """Построение конфигурация внешней инфраструктуры."""
        binder.bind(aiohttp.ClientSession, to=connection.session_factory(POOL_SIZE))
        binder.bind(
            motor_asyncio.AsyncIOMotorClient,
            to=motor_asyncio.AsyncIOMotorClient(MONGO_URI, tz_aware=False),
        )
        binder.bind(mapper.Mapper, to=mapper.Mapper(mapper.DATA_MAPPING))

    @injector.provider
    def logger_type(self) -> Type[logger.AsyncLogger]:
        """Предоставляет класс асинхронного логгера."""
        return logger.AsyncLogger
