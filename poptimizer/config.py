"""Основные настраиваемые параметры."""
import logging
import pathlib
from typing import Union
import pandas as pd
import torch
import yaml

from poptimizer.shared.log import get_handlers


class POptimizerError(Exception):
    """Базовое исключение."""


# Конфигурация логгера
logging.basicConfig(level=logging.INFO, handlers=get_handlers())

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


def _load_config() -> dict[str, Union[int, float, str]]:
    cfg = {}
    path = _root / "config" / "config.yaml"
    if path.exists():
        with path.open() as path:
            cfg = yaml.safe_load(path)

    logging.getLogger("Config").info(f"{cfg}")

    return cfg


_cfg = _load_config()

# Количество торговых дней в месяце и в году
MONTH_IN_TRADING_DAYS = 21
YEAR_IN_TRADING_DAYS = 12 * MONTH_IN_TRADING_DAYS

# Загрузка конфигурации
TARGET_POPULATION = _cfg.get("TARGET_POPULATION", 100)
FORECAST_DAYS = _cfg.get("FORECAST_DAYS", 21)
HISTORY_DAYS_MIN = _cfg.get("HISTORY_DAYS_MIN", 63)
P_VALUE = _cfg.get("P_VALUE", 0.05)
COSTS = _cfg.get("COSTS", 0.025) / 100 * (YEAR_IN_TRADING_DAYS / FORECAST_DAYS)
MARKET_IMPACT_FACTOR = _cfg.get("MARKET_IMPACT_FACTOR", 1)
START_EVOLVE_HOUR = _cfg.get("START_EVOLVE_HOUR", 1)
STOP_EVOLVE_HOUR = _cfg.get("STOP_EVOLVE_HOUR", 1)
OPTIMIZER = _cfg.get("OPTIMIZER", "resample")
