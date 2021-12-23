"""Содержит стандартные настройки логирования.

Логирование идет stdout и файл с ротацией.
"""
import datetime
import gzip
import os
import sys
from logging import Formatter, Handler, LogRecord, StreamHandler, handlers
from pathlib import Path
from typing import Optional


class _UtcMicrosecondsFormatter(Formatter):
    def __init__(self) -> None:
        super().__init__(
            "{asctime} | {levelname} | {name} | {filename} | line#{lineno} | pid#{process} | {message}",
            datefmt="%Y-%m-%d %H:%M:%S.%f",  # noqa: WPS323
            style="{",
        )

    def formatTime(self, record: LogRecord, datefmt: Optional[str] = None) -> str:  # noqa: N802
        ct = datetime.datetime.utcfromtimestamp(record.created)
        if datefmt:
            return ct.strftime(datefmt)

        time = ct.strftime("%Y-%m-%d %H:%M:%S")

        return f"{time}.{record.msecs}"


def _rotator(source: str, dest: str) -> None:
    with open(source, "rb") as sf:
        compressed = gzip.compress(sf.read(), 9)
        with open(dest, "wb") as df:
            df.write(compressed)
    os.remove(source)


def _namer(default_name: str) -> str:
    return f"{default_name}.gz"


def get_handlers(
    logs_path: Path,
    rotate_mega_bytes: int = 2,
    rotate_count: int = 5,
) -> list[Handler]:
    """Настраивает логирование в stdout и файл с ротацией."""
    logs_path.mkdir(exist_ok=True)
    file_handler = handlers.RotatingFileHandler(
        filename=logs_path / "lgr.lgr",
        encoding="utf-8",
        maxBytes=rotate_mega_bytes * 1024 ** 2,
        backupCount=rotate_count,
        delay=False,
    )
    file_handler.rotator = _rotator
    file_handler.namer = _namer
    file_handler.setFormatter(_UtcMicrosecondsFormatter())

    stream_handler = StreamHandler(sys.stdout)
    stream_handler.setFormatter(Formatter("{message}", style="{"))

    return [file_handler, stream_handler]
