"""Класс с данными, который хранит и автоматически обновляет дату последнего изменения данных."""
import logging
from typing import Any

import aiomoex
import pandas as pd

from poptimizer import config
from poptimizer.storage import store
from poptimizer.storage.store import MAX_SIZE, MAX_DBS

# Часовой пояс MOEX
MOEX_TZ = "Europe/Moscow"

# Торги заканчиваются в 19.00, но данные публикуются 19.45
END_OF_TRADING = dict(hour=19, minute=45, second=0, microsecond=0, nanosecond=0)

# Ключ в хранилище с датой последней исторической котировкой на MOEX
LAST_HISTORY = "last_history"


class Datum:
    """Класс с данными, который хранит и автоматически обновляет дату последнего изменения данных."""

    def __init__(self, value: Any):
        self._value = value
        self._last_update = pd.Timestamp.now(MOEX_TZ)

    @property
    def value(self):
        """Данные."""
        return self._value

    @value.setter
    def value(self, value: Any):
        self._value = value
        self._last_update = pd.Timestamp.now(MOEX_TZ)

    @property
    def timestamp(self):
        """Время обновления в формате pd.Timestamp в часовом поясе MOEX."""
        return self._last_update


async def download_last_history():
    """Последняя дата торгов, которая есть на MOEX ISS."""
    dates = await aiomoex.get_board_dates()
    date = pd.Timestamp(dates[0]["till"], tz=MOEX_TZ)
    date += pd.DateOffset(**END_OF_TRADING)
    logging.info(f"Загружена последняя дата с историей: {date}")
    return date + pd.DateOffset(**END_OF_TRADING)


async def update_timestamp():
    """Момент времени после, которого не нужно обновлять исторические данные."""
    now = pd.Timestamp.now(MOEX_TZ)
    # noinspection PyUnresolvedReferences
    end_of_trading = now.normalize() + pd.DateOffset(**END_OF_TRADING)
    if end_of_trading > now:
        end_of_trading += pd.DateOffset(days=-1)
    with store.DataStore(config.DATA_PATH, MAX_SIZE, MAX_DBS) as db:
        last_history = db[LAST_HISTORY]
        if last_history is None or last_history.timestamp < end_of_trading:
            last_history = Datum(await download_last_history())
            db[LAST_HISTORY] = last_history
    return last_history.value
