"""Основные настраиваемые параметры"""
import logging
import pathlib

import pandas as pd


class POptimizerError(Exception):
    """Базовое исключение."""


# Конфигурация логгера
logging.basicConfig(level=logging.INFO)

# Количество колонок в распечатках без переноса на несколько страниц
pd.set_option("display.max_columns", 20)
pd.set_option("display.max_rows", 70)
pd.set_option("display.width", None)

# Путь к директории с данными
DATA_PATH = pathlib.Path(__file__).parents[1] / "data"

# Путь к директории с отчетам
REPORTS_PATH = pathlib.Path(__file__).parents[1] / "reports"

# Множитель, для переходя к после налоговым значениям
AFTER_TAX = 1 - 0.13

# Параметр для доверительных интервалов
T_SCORE = 2.0

# Максимальный объем одной торговой операции в долях портфеля
MAX_TRADE = 0.01

# Период в торговых днях, за который медианный оборот торгов
TURNOVER_PERIOD = 21

# Минимальный оборот - преимущества акции снижаются при приближении медианного оборота к данному уровню
TURNOVER_CUT_OFF = 4.7 * MAX_TRADE

# Параметры ML-модели
ML_PARAMS = (
    (
        ("Label", {"days": 22}),
        ("STD", {"days": 23}),
        ("Ticker", {}),
        ("Mom12m", {"days": 245}),
        ("DivYield", {"days": 275}),
        ("Mom1m", {"days": 23}),
        ("RetMax", {"days": 18}),
    ),
    {
        "bagging_temperature": 0.5840511654727687,
        "depth": 6,
        "l2_leaf_reg": 1.6751871326946743,
        "learning_rate": 0.012260830377916065,
        "one_hot_max_size": 100,
        "random_strength": 0.8185547547078572,
        "ignored_features": [],
    },
)
