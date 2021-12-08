"""Содержит стандартные настройки логирования.

Логирование идет stderr и файл с ротацией.
"""
import datetime
import os
import sys
import zlib
from logging import Formatter, StreamHandler
from logging.handlers import RotatingFileHandler
from pathlib import Path


class UtcMicrosecondsFormatter(Formatter):
    def formatTime(self, record, datefmt=None):
        ct = datetime.datetime.utcfromtimestamp(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y-%m-%d %H:%M:%S")
            s = "%s.%03d" % (t, record.msecs)
        return s


def rotator(source, dest):
    with open(source, "rb") as sf:
        data = sf.read()
        compressed = zlib.compress(data, 9)
        with open(dest, "wb") as df:
            df.write(compressed)
    os.remove(source)


def namer(default_name: str) -> str:
    return default_name + ".gz"


def get_formatter():
    return UtcMicrosecondsFormatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(filename)s | line#%(lineno)d | pid#%(process)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S.%f",
    )


def get_handlers(logs_path: Path, rotate_mega_bytes: int = 2, rotate_count: int = 5):
    logs_path.mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        filename=logs_path / "log.log",
        encoding="utf-8",
        maxBytes=rotate_mega_bytes * 1024 ** 2,
        backupCount=rotate_count,
        delay=False,
    )
    file_handler.rotator = rotator
    file_handler.namer = namer
    file_handler.setFormatter(get_formatter())

    stream_handler = StreamHandler(sys.stdout)
    stream_handler.setFormatter(Formatter("%(message)s"))

    return [file_handler, stream_handler]
