"""Основные настраиваемые параметры."""
import logging
import pathlib
from typing import Union, cast, Final
import pandas as pd
import torch
import yaml

from poptimizer.shared.log import get_handlers


class POptimizerError(Exception):
    """Базовое исключение."""


# Устройство на котором будет производиться обучение
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Количество колонок в распечатках без переноса на несколько страниц
pd.set_option("display.max_columns", 20)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", None)

_root = pathlib.Path(__file__).parents[1]

# Путь к директории с отчетами
REPORTS_PATH = _root / "reports"

# Путь к директории с портфелями
PORT_PATH = _root / "portfolio"

# Путь к директории с логами
LOG_PATH = _root / "logs"

# Конфигурация логгера
logging.basicConfig(level=logging.INFO, handlers=get_handlers(LOG_PATH))


def _load_config() -> dict[str, Union[int, float, str]]:
    cfg = {}
    path = _root / "config" / "config.yaml"
    if path.exists():
        with path.open() as file:
            cfg = yaml.safe_load(file)

    logging.getLogger("Config").info(f"{cfg}")

    return cfg


_cfg = _load_config()

# Количество торговых дней в месяце и в году
MONTH_IN_TRADING_DAYS = 21
YEAR_IN_TRADING_DAYS = 12 * MONTH_IN_TRADING_DAYS

# Загрузка конфигурации
FORECAST_DAYS = cast(int, _cfg.get("FORECAST_DAYS", 21))
FORECAST_DIV = cast(float, _cfg.get("FORECAST_DIV", 0))
HISTORY_DAYS_MIN = cast(int, _cfg.get("HISTORY_DAYS_MIN", 3))
P_VALUE = cast(float, _cfg.get("P_VALUE", 0.05))
COSTS = cast(float, _cfg.get("COSTS", 0.04)) / 100
TRADING_INTERVAL = cast(int, _cfg.get("TRADING_INTERVAL", 1))
START_EVOLVE_HOUR = cast(int, _cfg.get("START_EVOLVE_HOUR", 1))
STOP_EVOLVE_HOUR = cast(int, _cfg.get("STOP_EVOLVE_HOUR", 1))
OPTIMIZER = cast(str, _cfg.get("OPTIMIZER", "resample"))
MIN_TEST_DAYS: Final = 11 * MONTH_IN_TRADING_DAYS
TARGET_POPULATION: Final = 100
