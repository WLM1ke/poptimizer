"""Настройки логирования."""
import logging
import sys
import types
from typing import Final, Literal


class ColorFormatter(logging.Formatter):
    """Цветное логирование."""

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
        fmt: str = "{asctime} {levelname} {name}: {message}",
        datefmt: str = "%Y-%m-%d %H:%M:%S",
        style: Literal["%", "{", "$"] = "{",
    ) -> None:
        """Инициализирует базовый логер."""
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)

    def format(self, record: logging.LogRecord) -> str:
        """Подменяет отображение уровня логирования цветным аналогом."""
        record.levelname = self.levels[record.levelno]

        return super().format(record)


def config(level: int = logging.INFO) -> None:
    """Настраивает логирование."""
    stream_formatter = ColorFormatter(
        fmt="{asctime} {levelname} {name}: {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(stream_formatter)

    logging.basicConfig(
        level=level,
        handlers=[stream_handler],
    )
