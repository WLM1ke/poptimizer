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
pd.set_option("display.max_rows", 80)
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
TURNOVER_PERIOD = 21 * 4

# Минимальный оборот - преимущества акции снижаются при приближении медианного оборота к данному уровню
TURNOVER_CUT_OFF = 3.6 * MAX_TRADE

# Параметры ML-модели
ML_PARAMS = {
    "data": (
        ("Label", {"days": 61, "div_share": 0.1, "on_off": True}),
        ("Scaler", {"days": 44, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 234, "on_off": True, "periods": 1}),
        ("DivYield", {"days": 345, "on_off": True, "periods": 1}),
        ("Mom1m", {"days": 28, "on_off": False}),
        ("RetMax", {"days": 56, "on_off": True}),
        ("ChMom6m", {"days": 81, "on_off": True}),
        ("STD", {"days": 21, "on_off": False}),
    ),
    "model": {
        "bagging_temperature": 0.8781174975146424,
        "depth": 10,
        "l2_leaf_reg": 3.515350536008831,
        "learning_rate": 0.0022148662986490974,
        "one_hot_max_size": 100,
        "random_strength": 0.4680819510519724,
    },
}
