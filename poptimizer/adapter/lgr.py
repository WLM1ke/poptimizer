import logging
import sys
import types
from copy import copy
from typing import Final, Literal

_LOGGER_NAME_SIZE: Final = 11


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
        fmt: str = "{asctime} {levelname} {message}",
        datefmt: str = "%Y-%m-%d %H:%M:%S",
        style: Literal["%", "{", "$"] = "{",
    ) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)

    def formatMessage(self, record: logging.LogRecord) -> str:  # noqa: N802
        record = copy(record)
        record.levelname = self.levels[record.levelno]
        record.name = f"{record.name}:".ljust(_LOGGER_NAME_SIZE)

        return super().formatMessage(record)


def init() -> logging.Logger:
    color_handler = logging.StreamHandler(sys.stdout)
    color_handler.setFormatter(_ColorFormatter())

    logging.basicConfig(
        level=logging.INFO,
        handlers=[color_handler],
    )
    logging.getLogger("pymongo").setLevel(logging.CRITICAL)

    return logging.getLogger()
