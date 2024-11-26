from pathlib import Path

from pydantic import HttpUrl, MongoDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Cfg(BaseSettings):
    telegram_token: str = ""
    telegram_chat_id: str = ""
    server_url: HttpUrl = HttpUrl("http://localhost:5000")
    mongo_db_uri: MongoDsn = MongoDsn("mongodb://localhost:27017")
    mongo_db_db: str = "poptimizer"

    model_config = SettingsConfigDict(
        env_file=Path(".env"),
        env_file_encoding="utf-8",
    )
