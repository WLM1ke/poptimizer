"""Настройки приложения."""
from pathlib import Path
from typing import Final

from pydantic import BaseModel, BaseSettings, Field, MongoDsn

_MAX_ISS_REQUESTS: Final = 20
_DEFAULT_PORT: Final = 5000
ROOT_PATH: Final = Path(__file__).parents[1]


class Mongo(BaseSettings):
    """Настройки MongoDB."""

    uri: MongoDsn = MongoDsn("localhost", scheme="mongodb")
    db: str = "data"


class HTTPClient(BaseSettings):
    """Настройки HTTP-клиента."""

    pool_size: int = Field(default=_MAX_ISS_REQUESTS, gt=0)


class Telegram(BaseSettings):
    """Настройки Телеграмма для отправки сообщений об ошибках."""

    token: str
    chat_id: str


class Server(BaseSettings):
    """Настройки сервера."""

    host: str = "localhost"
    port: int = _DEFAULT_PORT


class Config(BaseModel):
    """Настройки приложения."""

    mongo: Mongo = Mongo()
    http_client: HTTPClient = HTTPClient()
    telegram: Telegram = Telegram()
    server: Server = Server()
