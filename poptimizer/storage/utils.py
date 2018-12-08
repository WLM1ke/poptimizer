"""Вспомогательные функции и класс для организации хранения данных."""
import logging
from dataclasses import dataclass, field
from typing import Any

import aiomoex
import pandas as pd

from poptimizer.storage import store

# Часовой пояс MOEX
MOEX_TZ = "Europe/Moscow"

# Торги заканчиваются в 19.00, но данные публикуются 19.45
END_OF_TRADING = dict(hour=19, minute=45, second=0, microsecond=0, nanosecond=0)

# Ключ в хранилище с датой последней исторической котировкой на MOEX
LAST_HISTORY = "last_history"

# Метки столбцов данных
DATE = "DATE"
CLOSE = "CLOSE"
VALUE = "VALUE"
TICKER = "TICKER"
REG_NUMBER = "REG_NUMBER"
LOT_SIZE = "LOT_SIZE"


@dataclass(frozen=True)
class Datum:
    """Класс с данными и датой создания в часовом поясе MOEX."""

    value: Any
    timestamp: pd.Timestamp = field(default_factory=lambda: pd.Timestamp.now(MOEX_TZ))


async def download_last_history():
    """Последняя дата торгов, которая есть на MOEX ISS."""
    dates = await aiomoex.get_board_dates()
    date = pd.Timestamp(dates[0]["till"], tz=MOEX_TZ)
    logging.info(f"Последняя дата с историей: {date}")
    return date + pd.DateOffset(**END_OF_TRADING)


async def update_timestamp(db: store.DataStore):
    """Момент времени после, которого не нужно обновлять исторические данные для хранилища."""
    now = pd.Timestamp.now(MOEX_TZ)
    # noinspection PyUnresolvedReferences
    end_of_trading = now.normalize() + pd.DateOffset(**END_OF_TRADING)
    if end_of_trading > now:
        end_of_trading += pd.DateOffset(days=-1)
    last_history = db[LAST_HISTORY]
    if last_history is None or last_history.timestamp < end_of_trading:
        last_history = Datum(await download_last_history())
        db[LAST_HISTORY] = last_history
    return last_history.value
