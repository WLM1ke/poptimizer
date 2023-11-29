import logging
from datetime import timedelta
from pathlib import Path
from typing import Annotated, Final

from pydantic import BaseModel, MongoDsn, PositiveInt, UrlConstraints
from pydantic_core import MultiHostUrl, Url
from pydantic_settings import BaseSettings, SettingsConfigDict

_MAX_ISS_REQUESTS: Final = 10
_RETRIES: Final = 3
_FIRST_RETRY: Final = timedelta(seconds=600)
_BACKOFF_FACTOR: Final = 2


class Logger(BaseModel):
    level: int | str = logging.INFO


class Telegram(BaseModel):
    token: str = ""
    chat_id: str = ""


class MongoClient(BaseModel):
    uri: MongoDsn = MultiHostUrl("mongodb://localhost:27017")


class HTTPClient(BaseModel):
    con_per_host: PositiveInt = _MAX_ISS_REQUESTS
    retries: int = _RETRIES
    first_retry: timedelta = _FIRST_RETRY
    backoff_factor: float = _BACKOFF_FACTOR


NatsDsn = Annotated[
    Url,
    UrlConstraints(
        allowed_schemes=["nats"],
        default_port=4222,
    ),
]


class NatsClient(BaseModel):
    host: NatsDsn = NatsDsn("nats://localhost:4222")


class Cfg(BaseSettings):
    logger: Logger = Logger()
    telegram: Telegram = Telegram()
    http_client: HTTPClient = HTTPClient()
    mongo_client: MongoClient = MongoClient()
    nats_client: NatsClient = NatsClient()

    model_config = SettingsConfigDict(
        env_file=Path(".env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )
