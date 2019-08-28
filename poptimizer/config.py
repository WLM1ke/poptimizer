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
MAX_TRADE = 0.01

# Период в торговых днях, за который медианный оборот торгов
TURNOVER_PERIOD = 21 * 4

# Минимальный оборот - преимущества акции снижаются при приближении медианного оборота к данному уровню
TURNOVER_CUT_OFF = 3.5 * MAX_TRADE

# Параметры ML-модели
ML_PARAMS = {
    "data": (
        ("Label", {"days": 45, "div_share": 0.2, "on_off": True}),
        ("Scaler", {"days": 226, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 180, "on_off": True, "periods": 2}),
        ("DivYield", {"days": 293, "on_off": True, "periods": 1}),
        ("Mom1m", {"days": 40, "on_off": False}),
        ("RetMax", {"days": 54, "on_off": True}),
        ("ChMom6m", {"days": 116, "on_off": True}),
        ("STD", {"days": 28, "on_off": True}),
    ),
    "model": {
        "bagging_temperature": 0.7454028153237059,
        "depth": 13,
        "l2_leaf_reg": 1.5334889818863198,
        "learning_rate": 0.006856219177323222,
        "one_hot_max_size": 2,
        "random_strength": 0.47064589449064304,
    },
}
