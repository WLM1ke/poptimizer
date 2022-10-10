"""Основные константы."""
from datetime import datetime
from pathlib import Path
from typing import Final

import torch

# Корень проекта для адресации к статическим файлам и бэкапам.
ROOT_PATH: Final = Path(__file__).parents[2]

# Автоматический выбор GPU для PyTorch
DEVICE: Final = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Множитель для получения дивидендов за вычетом налогов
AFTER_TAX: Final = 0.87

# Дата, с которой собираются дивиденды.
_START_YEAR: Final = 2015
START_DATE: Final = datetime(_START_YEAR, 1, 1)

MONTH_IN_TRADING_DAYS: Final = 21
_MONTHS_IN_YEAR: Final = 12
YEAR_IN_TRADING_DAYS: Final = MONTH_IN_TRADING_DAYS * _MONTHS_IN_YEAR

DEFAULT_HISTORY_DAYS: Final = YEAR_IN_TRADING_DAYS
_MINIMUM_TESTS: Final = 200
LIQUIDITY_DAYS_LOWER: Final = MONTH_IN_TRADING_DAYS
LIQUIDITY_DAYS_UPPER: Final = (DEFAULT_HISTORY_DAYS + _MINIMUM_TESTS) * 2
