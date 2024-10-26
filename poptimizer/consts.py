from datetime import date
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).parents[1]

# Дата, с которой собираются дивиденды
START_DAY: Final = date(2015, 1, 1)
AFTER_TAX: Final = 0.85
MONTH_IN_TRADING_DAYS: Final = 21
YEAR_IN_TRADING_DAYS: Final = 21 * 12
