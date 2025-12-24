from pathlib import Path
from typing import Final

from pydantic import BaseModel, HttpUrl, MongoDsn
from pydantic_settings import (
    BaseSettings,
    CliSuppress,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from poptimizer import consts

_CFG_FILE: Final = consts.ROOT / "cfg" / "cfg.yaml"
_ENV_FILE: Final = consts.ROOT / ".env"
_CFG_TEMPLATE: Final = """tg:
  token: "{token}"
  chat_id: {chat_id}
server:
  url: "{server_url}"
mongo:
  uri: "{mongo_db_uri}"
  db: "{mongo_db_db}"
"""


class _Cfg(BaseSettings):
    telegram_token: str = ""
    telegram_chat_id: int = 0
    server_url: HttpUrl = HttpUrl("http://localhost:5000")
    mongo_db_uri: MongoDsn = MongoDsn("mongodb://localhost:27017")
    mongo_db_db: str = "poptimizer"

    model_config = SettingsConfigDict(
        env_file=Path(".env"),
        env_file_encoding="utf-8",
    )


class Telegram(BaseModel):
    token: str = ""
    chat_id: int = 0


class Server(BaseModel):
    url: HttpUrl = HttpUrl("http://localhost:5000")


class Mongo(BaseModel):
    uri: MongoDsn = MongoDsn("mongodb://localhost:27017")
    db: str = "poptimizer"


class Cfg(BaseSettings):
    tg: CliSuppress[Telegram] = Telegram()
    server: CliSuppress[Server] = Server()
    mongo: CliSuppress[Mongo] = Mongo()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,  # noqa: ARG003
        dotenv_settings: PydanticBaseSettingsSource,  # noqa: ARG003
        file_secret_settings: PydanticBaseSettingsSource,  # noqa: ARG003
    ) -> tuple[
        PydanticBaseSettingsSource,
        YamlConfigSettingsSource,
    ]:
        return (
            init_settings,
            YamlConfigSettingsSource(settings_cls, yaml_file=_CFG_FILE, yaml_file_encoding="utf-8"),
        )


def migrate_cfg() -> None:
    if _CFG_FILE.exists():
        return

    _CFG_FILE.parent.mkdir(parents=True, exist_ok=True)

    cfg_v1 = _Cfg()

    cfg_str = _CFG_TEMPLATE.format(
        token=cfg_v1.telegram_token,
        chat_id=cfg_v1.telegram_chat_id,
        server_url=cfg_v1.server_url,
        mongo_db_uri=cfg_v1.mongo_db_uri,
        mongo_db_db=cfg_v1.mongo_db_db,
    )

    with _CFG_FILE.open("w", encoding="utf-8") as cfg_file:
        cfg_file.write(cfg_str)

    _ENV_FILE.unlink()
