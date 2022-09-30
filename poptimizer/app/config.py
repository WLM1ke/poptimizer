"""Настройки приложения."""
import logging
from typing import Final

from pydantic import BaseModel, BaseSettings, Field, MongoDsn

_MAX_ISS_REQUESTS: Final = 10
_DEFAULT_PORT: Final = 5000


class Logger(BaseSettings):
    """Настройки логирования - сообщения выше уровня INFO дублируются в Телеграм."""

    app_name: str = "POptimizer"
    level: int | str = logging.INFO
    telegram_token: str
    telegram_chat_id: str


class Mongo(BaseSettings):
    """Настройки MongoDB."""

    uri: MongoDsn = MongoDsn("localhost", scheme="mongodb")


class HTTPClient(BaseSettings):
    """Настройки HTTP-клиента."""

    con_per_host: int = Field(default=_MAX_ISS_REQUESTS, gt=0)


class Resources(BaseModel):
    """Настройки приложения."""

    logger: Logger = Logger()
    mongo: Mongo = Mongo()
    http_client: HTTPClient = HTTPClient()


class Server(BaseSettings):
    """Настройки сервера."""

    host: str = "localhost"
    port: int = _DEFAULT_PORT
