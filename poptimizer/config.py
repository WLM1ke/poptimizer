from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, MongoDsn, UrlConstraints
from pydantic_core import MultiHostUrl, Url
from pydantic_settings import BaseSettings, SettingsConfigDict


class Logger(BaseModel):
    level: int | str = "INFO"


class Telegram(BaseModel):
    token: str = ""
    chat_id: str = ""


class MongoDB(BaseModel):
    uri: MongoDsn = MultiHostUrl("mongodb://localhost:27017")


NatsDsn = Annotated[
    Url,
    UrlConstraints(
        allowed_schemes=["nats"],
        default_port=4222,
    ),
]


class Nats(BaseModel):
    uri: NatsDsn = NatsDsn("nats://localhost:4222")


class Cfg(BaseSettings):
    logger: Logger = Logger()
    telegram: Telegram = Telegram()
    mongo_db: MongoDB = MongoDB()
    nats: Nats = Nats()

    model_config = SettingsConfigDict(
        env_file=Path(".env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )
