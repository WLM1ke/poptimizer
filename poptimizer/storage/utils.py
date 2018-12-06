"""Класс с данными, который хранит и автоматически обновляет дату последнего изменения данных."""
import asyncio
import logging
from typing import Any

import aiomoex
import pandas as pd

# Часовой пояс MOEX
from poptimizer.config import DATA_PATH
from poptimizer.storage import store
from poptimizer.storage.store import MAX_SIZE, MAX_DBS

MOEX_TZ = "Europe/Moscow"

# Торги заканчиваются в 19.00, но данные публикуются 19.45
END_OF_TRADING_TIME = dict(hour=19, minute=45, second=0, microsecond=0)

# Ключ с датой последней исторической котировкой на MOEX
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


async def down_load_last_history():
    """Последняя дата торгов, которая есть на MOEX ISS"""
    async with aiomoex.ISSClientSession():
        dates = await aiomoex.get_board_dates()
        date = pd.Timestamp(dates[0]["till"], tz=MOEX_TZ)
        date += pd.DateOffset(**END_OF_TRADING_TIME)
        logging.info(f"Загружена последняя дата с историей: {date}")
        return date + pd.DateOffset(**END_OF_TRADING_TIME)


def update_timestamp():
    """Момент времени после, которого не нужно обновлять исторические данные"""
    now = pd.Timestamp.now(MOEX_TZ)
    # noinspection PyUnresolvedReferences
    end_of_trading = now.normalize() + pd.DateOffset(**END_OF_TRADING_TIME)
    if end_of_trading > now:
        end_of_trading += pd.DateOffset(days=-1)
    with store.DataStore(DATA_PATH, MAX_SIZE, MAX_DBS) as db:
        last_history = db[LAST_HISTORY]
        if last_history is None or last_history.timestamp < end_of_trading:
            last_history = Datum(asyncio.run(down_load_last_history()))
            db[LAST_HISTORY] = last_history
    return last_history.value
