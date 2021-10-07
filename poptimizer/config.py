"""Основные настраиваемые параметры."""
import logging
import pathlib

import pandas as pd
import torch


class POptimizerError(Exception):
    """Базовое исключение."""


# Конфигурация логгера
logging.basicConfig(level=logging.INFO)

# Устройство на котором будет производиться обучение
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Количество колонок в распечатках без переноса на несколько страниц
pd.set_option("display.max_columns", 20)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", None)

# Путь к директории с отчетами
REPORTS_PATH = pathlib.Path(__file__).parents[1] / "reports"

# Путь к директории с портфелями
PORT_PATH = pathlib.Path(__file__).parents[1] / "portfolio"

# Количество торговых дней в году
YEAR_IN_TRADING_DAYS = 12 * 21

# Минимальное количество моделей в ансамбле
TARGET_POPULATION = 150

# Длинна прогноза в торговых днях
FORECAST_DAYS = 37

# Минимальная количество дней истории котировок для прогнозов
HISTORY_DAYS_MIN = 79

# Значимость отклонения градиента от нуля
P_VALUE = 0.05

# Транзакционные издержки на одну сделку
COSTS = (YEAR_IN_TRADING_DAYS / FORECAST_DAYS) * (0.025 / 100)

# Market impact в дневном СКО при операциях на уровне дневного объема
MARKET_IMPACT_FACTOR = 1
