"""Настройки приложения."""
import os
from dataclasses import dataclass


class POError(Exception):
    """Базовая ошибка приложения."""

    def __str__(self) -> str:
        """Выводи исходную причину ошибки при ее наличии для удобства логирования.

        https://peps.python.org/pep-3134/
        """
        current = super().__str__()
        cause_err = self.__cause__ or self.__context__

        if not cause_err:
            return f"-> {current}"

        cause = repr(cause_err)
        if not isinstance(cause_err, POError):
            cause = f"-> {cause}"

        return f"-> {current} {cause}"

    def __repr__(self) -> str:
        """Выводи исходную причину ошибки при ее наличии для удобства логирования.

        https://peps.python.org/pep-3134/
        """
        return str(self)


def evn_reader(*, env_name: str, default: str = "") -> str:
    """Читает переменную окружения, удаляя во время чтения."""
    return os.environ.pop(env_name, default)


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
