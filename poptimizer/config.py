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
MAX_TRADE = 0.011

# Период в торговых днях, за который медианный оборот торгов
TURNOVER_PERIOD = 21

# Минимальный оборот - преимущества акции снижаются при приближении медианного оборота к данному уровню
TURNOVER_CUT_OFF = 4.7 * MAX_TRADE

# Параметры ML-модели
ML_PARAMS = (
    (
        ("Label", {"days": 24}),
        ("STD", {"days": 20}),
        ("Ticker", {}),
        ("Mom12m", {"days": 237}),
        ("DivYield", {"days": 273}),
        ("Mom1m", {"days": 26}),
        ("RetMax", {"days": 25}),
    ),
    {
        "bagging_temperature": 1.0119313141226849,
        "depth": 6,
        "l2_leaf_reg": 2.664570812697747,
        "learning_rate": 0.011398942556206918,
        "one_hot_max_size": 100,
        "random_strength": 0.5599905025336634,
        "ignored_features": [],
    },
)
