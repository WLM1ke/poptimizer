"""Настройки приложения."""
from typing import Final

from pydantic import BaseModel, BaseSettings, Field, MongoDsn

_MAX_ISS_REQUESTS: Final = 20


class Mongo(BaseSettings):
    """Настройки MongoDB."""

    uri: MongoDsn = MongoDsn("localhost", scheme="mongodb")
    db: str = "data"


class HTTPClient(BaseModel):
    """Настройки HTTP-клиента."""

    pool_size: int = Field(default=_MAX_ISS_REQUESTS, gt=0)


class Telegram(BaseSettings):
    """Настройки Телеграмма для отправки сообщений об ошибках."""

    token: str
    chat_id: str


class Config(BaseModel):
    """Настройки приложения."""

    mongo: Mongo = Mongo()
    http_client: HTTPClient = HTTPClient()
    telegram: Telegram = Telegram()
