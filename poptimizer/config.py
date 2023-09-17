import logging
from pathlib import Path
from typing import Annotated, Final

import pydantic_settings
from pydantic import MongoDsn, PositiveInt, UrlConstraints
from pydantic_core import MultiHostUrl, Url

_MAX_ISS_REQUESTS: Final = 10


class BaseSettings(pydantic_settings.BaseSettings):

    model_config = pydantic_settings.SettingsConfigDict(
        env_file=Path(".env"),
        env_file_encoding="utf-8",
        hide_input_in_errors=True,
        extra="ignore",
    )


class Logger(BaseSettings):

    level: int | str = logging.INFO
    telegram_level: int | str = logging.WARNING
    telegram_token: str = ""
    telegram_chat_id: str = ""


class MongoClient(BaseSettings):

    uri: MongoDsn = MultiHostUrl("mongodb://localhost:27017")


class HTTPClient(BaseSettings):

    con_per_host: PositiveInt = _MAX_ISS_REQUESTS


NatsDsn = Annotated[
    Url,
    UrlConstraints(
        allowed_schemes=["nats"],
        default_port=4222,
    ),
]


class NatsClient(BaseSettings):

    host: NatsDsn = NatsDsn("nats://localhost:4222")


class Cfg(BaseSettings):

    logger: Logger = Logger()
    http_client: HTTPClient = HTTPClient()
    mongo_client: MongoClient = MongoClient()
    nats_client: NatsClient = NatsClient()
