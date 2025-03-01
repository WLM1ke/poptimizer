from datetime import date
from pathlib import Path
from typing import Final

__version__ = "3.0.0b1"

ROOT: Final = Path(__file__).parents[1]

# Дата, с которой собираются дивиденды
START_DAY: Final = date(2015, 1, 1)
P_VALUE: Final = 0.05
COSTS: Final = 0.04 / 100
IMPACT_COSTS_SCALE: Final = 1.5
AFTER_TAX: Final = 0.85
MONTH_IN_TRADING_DAYS: Final = 21
YEAR_IN_TRADING_DAYS: Final = 21 * 12

INITIAL_HISTORY_DAYS_START: Final = YEAR_IN_TRADING_DAYS
INITIAL_HISTORY_DAYS_END: Final = INITIAL_HISTORY_DAYS_START + MONTH_IN_TRADING_DAYS
INITIAL_FORECAST_DAYS: Final = 1
INITIAL_POPULATION: Final = YEAR_IN_TRADING_DAYS
