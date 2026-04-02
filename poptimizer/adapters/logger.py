import logging
import sys
import types
from collections.abc import Callable
from copy import copy
from typing import Final, Literal

from aiogram import loggers

from poptimizer.adapters import gmail

_IGNORE_LOGGER_NAMES: Final = (gmail.LOGGER_NAME, loggers.dispatcher.name)
_LOGGER_NAME_SIZE: Final = 13


class _GmailHandler(logging.Handler):
    def __init__(
        self,
        send_fn: Callable[[str], None],
    ) -> None:
        super().__init__(logging.WARNING)
        self._send_fn = send_fn

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name not in _IGNORE_LOGGER_NAMES

    def emit(self, record: logging.LogRecord) -> None:
        self._send_fn(record.getMessage())


class _ColorFormatter(logging.Formatter):
    levels: Final = types.MappingProxyType(
        {
            logging.DEBUG: "\033[90mDBG\033[0m",
            logging.INFO: "\033[34mINF\033[0m",
            logging.WARNING: "\033[31mWRN\033[0m",
            logging.ERROR: "\033[1;31mERR\033[0m",
            logging.CRITICAL: "\033[1;91mCRT\033[0m",
        },
    )

    def __init__(
        self,
        fmt: str = "{asctime} {levelname} {name} {message}",
        datefmt: str = "%Y-%m-%d %H:%M:%S",
        style: Literal["%", "{", "$"] = "{",
    ) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)

    def formatMessage(self, record: logging.LogRecord) -> str:  # noqa: N802
        record = copy(record)
        record.levelname = self.levels[record.levelno]
        record.name = f"{record.name}:".ljust(_LOGGER_NAME_SIZE)

        return super().formatMessage(record)


def init(send_fn: Callable[[str], None] | None = None) -> logging.Logger:
    color_handler = logging.StreamHandler(sys.stdout)
    color_handler.setFormatter(_ColorFormatter())
    handlers: list[logging.Handler] = [color_handler]

    if send_fn is not None:
        handlers.append(_GmailHandler(send_fn))

    logging.basicConfig(
        level=logging.INFO,
        handlers=handlers,
    )
    logging.getLogger("pymongo").setLevel(logging.CRITICAL)

    return logging.getLogger("App")
