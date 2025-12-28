import re
from pathlib import Path
from typing import Any, Final

import keyring
from pydantic import BaseModel, Field, HttpUrl, MongoDsn
from pydantic_settings import (
    BaseSettings,
    CliSuppress,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)

from poptimizer import consts
from poptimizer.domain import domain

KEYCHAIN_APP: Final = "poptimizer"
KEYCHAIN_PREFIX: Final = "keychain:"

_CFG_FILE: Final = consts.ROOT / "cfg" / "cfg.yaml"

_ACCOUNT_TOKEN_RE: Final = re.compile(r"^t[.][A-Za-z0-9._-]{86}$")
_ACCOUNT_NAME_RE: Final = re.compile(r"^[A-Za-z0-9]+$")
_ACCOUNT_ID_RE: Final = re.compile(r"^[0-9]{10}$")


def _ensure_config(file: Path) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    file.touch()


def _restrict_permissions_to_600(file: Path) -> None:
    current_mode = file.stat().st_mode
    new_mode = (current_mode & 0o7000) | (current_mode & 0o600)
    file.chmod(new_mode)


class _KeychainYamlSource(YamlConfigSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings], yaml_file: Path, yaml_file_encoding: str) -> None:
        _ensure_config(yaml_file)
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
