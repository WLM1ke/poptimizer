"""Конфигурация внешней инфраструктуры."""
from typing import Final, Type

import aiohttp
import injector
import pandas as pd
from motor import motor_asyncio

from poptimizer.data_di.adapters import connection
from poptimizer.data_di.shared import logger, mapper

# Размер пула http-соединений - при большем размере многие сайты ругаются
POOL_SIZE: Final = 20

# Ссылка на локальный MongoDB сервер
MONGO_URI: Final = "mongodb://localhost:27017"


# Описание мэппинга данных в MongoDB
DATA_MAPPING: Final = (
    mapper.Desc(
        field_name="_df",
        doc_name="data",
        factory_name="df",
        encoder=lambda df: df.to_dict("split"),
        decoder=lambda doc_df: pd.DataFrame(**doc_df),
    ),
    mapper.Desc(
        field_name="_timestamp",
        doc_name="timestamp",
        factory_name="timestamp",
    ),
)


class Adapters(injector.Module):
    """Конфигурация внешней инфраструктуры."""

    @injector.provider
    @injector.singleton
    def logger_type(self) -> Type[logger.AsyncLogger]:
        """Предоставляет класс асинхронного логгера."""
        return logger.AsyncLogger

    @injector.provider
    @injector.singleton
    def http_session(self) -> aiohttp.ClientSession:
        """Предоставляет единственную http-сессию."""
        return connection.session_factory(POOL_SIZE)

    @injector.provider
    @injector.singleton
    def db_session(self, logger_type: Type[logger.AsyncLogger]) -> mapper.MongoDBSession:
        """Предоставляет единственную сессию MongoDB."""
        return mapper.MongoDBSession(
            motor_asyncio.AsyncIOMotorClient(MONGO_URI, tz_aware=False),
            mapper.Mapper(DATA_MAPPING),
            logger_type,
        )
