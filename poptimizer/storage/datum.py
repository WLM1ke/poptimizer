"""Класс с данными, который хранит и автоматически обновляет дату последнего изменения данных."""
from typing import Any

import pandas as pd

from poptimizer.config import MOEX_TZ


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
    def last_update(self):
        """Время обновления в формате pd.Timestamp в часовом поясе MOEX."""
        return self._last_update
