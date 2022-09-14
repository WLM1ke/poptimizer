"""Основные константы."""
from datetime import datetime
from pathlib import Path
from typing import Final

# Дата, с которой собираются дивиденды.
_START_YEAR: Final = 2015
START_DATE: Final = datetime(_START_YEAR, 1, 1)

# Корень проекта для адресации к статическим файлам и бэкапам.
ROOT_PATH: Final = Path(__file__).parents[1]
