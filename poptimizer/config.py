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
MAX_TRADE = 0.017

# Период в торговых днях, за который медианный оборот торгов
TURNOVER_PERIOD = 21 * 3

# Минимальный оборот - преимущества акции снижаются при приближении медианного оборота к данному уровню
TURNOVER_CUT_OFF = 4.0 * MAX_TRADE

# Параметры ML-модели
ML_PARAMS = {
    "data": (
        ("Label", {"days": 44, "on_off": True}),
        ("STD", {"days": 26, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 255, "on_off": True}),
        ("DivYield", {"days": 304, "on_off": True, "periods": 1}),
        ("Mom1m", {"days": 29, "on_off": True}),
        ("RetMax", {"days": 40, "on_off": True}),
        ("ChMom6m", {"days": 114, "on_off": True}),
    ),
    "model": {
        "bagging_temperature": 1.0517537606447385,
        "depth": 9,
        "l2_leaf_reg": 3.470705441531027,
        "learning_rate": 0.006413498364479064,
        "one_hot_max_size": 2,
        "random_strength": 1.4033180342553484,
    },
}
