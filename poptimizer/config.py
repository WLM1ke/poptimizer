"""Основные настраиваемые параметры."""
import logging
import pathlib
import sys

import pandas as pd
import torch


class POptimizerError(Exception):
    """Базовое исключение."""


# Конфигурация логгера
logging.basicConfig(level=logging.INFO,
                    handlers=[logging.FileHandler("debug.log"), logging.StreamHandler(sys.stdout)])

# Устройство на котором будет производиться обучение
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu") #

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
TARGET_POPULATION = 200

# Длинна прогноза в торговых днях
FORECAST_DAYS = 34

# Минимальная количество дней истории котировок для прогнозов
HISTORY_DAYS_MIN = 88

# Значимость отклонения градиента от нуля
P_VALUE = 0.05

# Транзакционные издержки на одну сделку
COSTS = (YEAR_IN_TRADING_DAYS / FORECAST_DAYS) * (0.025 / 100)

# Market impact в дневном СКО при операциях на уровне дневного объема
MARKET_IMPACT_FACTOR = 1

# Временной диапазон, когда эволюция будет работать, если равны - будет работать бесконечно
# включительно
START_EVOLVE_HOUR = 1
# не включительно
STOP_EVOLVE_HOUR = 7

# Имена файлов пртфелей, используемых для обучения модлей
BASE_PORTS = {'dividend_port.yaml'}
# Имена файлов пртфелей, неиспользуемых для обучения модлей
NOT_USED_PORTS = {'base.yaml'}


