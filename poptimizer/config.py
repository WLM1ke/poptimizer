"""Настройки приложения."""
import os
from dataclasses import dataclass
from typing import Callable, TypeVar


class POptimizerError(Exception):
    """Базовая ошибка приложения."""


SettingsT = TypeVar("SettingsT")


def evn_reader(
    *,
    default: SettingsT,
    env_name: str,
    type_func: Callable[[str], SettingsT] | None = None,
) -> SettingsT:
    """Читает переменную окружения, удаляя во время чтения, и преобразует к нужному типу."""
    if (raw_value := os.environ.pop(env_name, None)) is None:
        return default

    if type_func is not None:
        return type_func(raw_value)

    if isinstance(raw_value, type(default)):
        return raw_value

    raise POptimizerError(f"Can't convert env variable {env_name} {raw_value}")


@dataclass(slots=True, frozen=True, kw_only=True)
class Mongo:
    """Настройки MongoDB."""

    uri: str = evn_reader(default="mongodb://localhost:27017", env_name="URI")
    db: str = evn_reader(default="data", env_name="DB")


@dataclass(slots=True, frozen=True, kw_only=True)
class HTTPClient:
    """Настройки HTTP-клиента."""

    pool_size: int = 20


@dataclass(slots=True, frozen=True, kw_only=True)
class Config:
    """Настройки приложения."""

    mongo: Mongo = Mongo()
    http_client: HTTPClient = HTTPClient()
