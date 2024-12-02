from datetime import date
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).parents[1]

# Дата, с которой собираются дивиденды
START_DAY: Final = date(2015, 1, 1)
P_VALUE: Final = 0.05
AFTER_TAX: Final = 0.85
MONTH_IN_TRADING_DAYS: Final = 21
YEAR_IN_TRADING_DAYS: Final = 21 * 12

INITIAL_HISTORY_DAYS_START: Final = YEAR_IN_TRADING_DAYS
INITIAL_HISTORY_DAYS_END: Final = INITIAL_HISTORY_DAYS_START + MONTH_IN_TRADING_DAYS
FORECAST_DAYS: Final = MONTH_IN_TRADING_DAYS
INITIAL_MINIMAL_REQUIRED_HISTORY_DAYS: Final = INITIAL_HISTORY_DAYS_END + FORECAST_DAYS + 1
