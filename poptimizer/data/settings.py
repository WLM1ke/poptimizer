"""Основные настройки пакета загрузки данных."""
import datetime
from typing import Final

# Дата начала статистики
_START_YEAR = 2015
STATS_START: Final = datetime.date(_START_YEAR, 1, 1)
