from pathlib import Path
from typing import Annotated

from pydantic import HttpUrl, MongoDsn, UrlConstraints
from pydantic_core import MultiHostUrl, Url
from pydantic_settings import BaseSettings, SettingsConfigDict

NatsDsn = Annotated[
    Url,
    UrlConstraints(
        allowed_schemes=["nats"],
        default_port=4222,
    ),
]


class Cfg(BaseSettings):
    log_level: int | str = "INFO"
    telegram_token: str = ""
    telegram_chat_id: str = ""
    server_url: HttpUrl = HttpUrl("http://localhost:5000")
    mongo_db_uri: MongoDsn = MultiHostUrl("mongodb://localhost:27017")
    nats_uri: NatsDsn = NatsDsn("nats://localhost:4222")

    model_config = SettingsConfigDict(
        env_file=Path(".env"),
        env_file_encoding="utf-8",
    )
