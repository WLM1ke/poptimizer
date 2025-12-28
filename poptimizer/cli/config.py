import re
from pathlib import Path
from typing import Any, Final

import keyring
from pydantic import BaseModel, Field, HttpUrl, MongoDsn
from pydantic_settings import (
    BaseSettings,
    CliSuppress,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from poptimizer import consts
from poptimizer.domain import domain

KEYCHAIN_APP: Final = "poptimizer"
KEYCHAIN_PREFIX: Final = "keychain:"
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

_ACCOUNT_TOKEN_RE: Final = re.compile(r"^t[.][A-Za-z0-9._-]{86}$")
_ACCOUNT_NAME_RE: Final = re.compile(r"^[A-Za-z0-9]+$")
_ACCOUNT_ID_RE: Final = re.compile(r"^[0-9]{10}$")


def _restrict_permissions_to_600(file: Path) -> None:
    current_mode = file.stat().st_mode
    new_mode = (current_mode & 0o7000) | (current_mode & 0o600)
    file.chmod(new_mode)


class _KeychainYamlSource(YamlConfigSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings], yaml_file: Path, yaml_file_encoding: str) -> None:
        _restrict_permissions_to_600(yaml_file)
        super().__init__(settings_cls, yaml_file, yaml_file_encoding)

    def _replace_from_keychain(self, data: dict[str, Any] | list[Any] | str) -> Any:
        match data:
            case dict():
                return {k: self._replace_from_keychain(v) for k, v in data.items()}
            case list():
                return [self._replace_from_keychain(i) for i in data]
            case str() if data.startswith(KEYCHAIN_PREFIX):
                secret_key = data.removeprefix(KEYCHAIN_PREFIX)
                secret_value = keyring.get_password(KEYCHAIN_APP, secret_key)

                if secret_value is None:
                    return data

                return secret_value
            case _:
                return data

    def __call__(self) -> dict[str, Any]:
        yaml_data = super().__call__()

        return self._replace_from_keychain(yaml_data)


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


class Account(BaseModel):
    token: str = Field(pattern=_ACCOUNT_TOKEN_RE)
    name: domain.AccName = Field(pattern=_ACCOUNT_NAME_RE)
    id: str = Field(pattern=_ACCOUNT_ID_RE)


class Brokers(BaseModel):
    tinkoff: list[Account] = Field(default_factory=list[Account])


class Cfg(BaseSettings):
    tg: CliSuppress[Telegram] = Telegram()
    server: CliSuppress[Server] = Server()
    mongo: CliSuppress[Mongo] = Mongo()
    brokers: CliSuppress[Brokers] = Brokers()

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
        _KeychainYamlSource,
    ]:
        return (
            init_settings,
            _KeychainYamlSource(settings_cls, yaml_file=_CFG_FILE, yaml_file_encoding="utf-8"),
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
