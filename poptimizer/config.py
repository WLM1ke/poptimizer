"""Настройки приложения."""
import os
from dataclasses import dataclass


class POptimizerError(Exception):
    """Базовая ошибка приложения."""


def evn_reader(*, env_name: str, default: str | None = None) -> str:
    """Читает переменную окружения, удаляя во время чтения."""
    raw_value = os.environ.pop(env_name, None) or default

    if not raw_value:
        raise POptimizerError(f"No default value for absent env variable {env_name}")

    return raw_value


@dataclass(slots=True, frozen=True, kw_only=True)
class Mongo:
    """Настройки MongoDB."""

    uri: str = evn_reader(env_name="URI", default="mongodb://localhost:27017")
    db: str = evn_reader(env_name="DB", default="data")


@dataclass(slots=True, frozen=True, kw_only=True)
class HTTPClient:
    """Настройки HTTP-клиента."""

    pool_size: int = 20


@dataclass(slots=True, frozen=True, kw_only=True)
class Telegram:
    """Настройки Телеграмма для отправки сообщений об ошибках."""

    token: str = evn_reader(env_name="TOKEN")
    chat_id: str = evn_reader(env_name="CHAT_ID")


@dataclass(slots=True, frozen=True, kw_only=True)
class Config:
    """Настройки приложения."""

    mongo: Mongo = Mongo()
    http_client: HTTPClient = HTTPClient()
    telegram: Telegram = Telegram()
