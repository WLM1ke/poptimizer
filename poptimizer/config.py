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

# Конфигурация MongoDB
MONGO_PATH = pathlib.Path(__file__).parents[1] / "db"
MONGO_LOG_PATH = pathlib.Path(__file__).parents[1] / "logs" / "mongodb.log"

# Множитель, для переходя к после налоговым значениям
AFTER_TAX = 1 - 0.13

# Параметр для доверительных интервалов
T_SCORE = 2.0

# Максимальный объем одной торговой операции в долях портфеля
MAX_TRADE = 0.01

# Период в торговых днях, за который медианный оборот торгов
TURNOVER_PERIOD = 21 * 4

# Минимальный оборот - преимущества акции снижаются при приближении медианного оборота к данному уровню
TURNOVER_CUT_OFF = 3.4 * MAX_TRADE

# Параметры ML-модели
ML_PARAMS = {
    "data": (
        ("Label", {"days": 67, "div_share": 0.2, "on_off": True}),
        ("Scaler", {"days": 249, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 177, "on_off": True, "periods": 2}),
        ("DivYield", {"days": 283, "on_off": True, "periods": 1}),
        ("Mom1m", {"days": 41, "on_off": True}),
        ("RetMax", {"days": 56, "on_off": True}),
        ("ChMom6m", {"days": 104, "on_off": True}),
        ("STD", {"days": 27, "on_off": True}),
        ("DayOfYear", {"on_off": False}),
    ),
    "model": {
        "bagging_temperature": 1.8634814925008159,
        "depth": 15,
        "l2_leaf_reg": 0.6819072098049954,
        "learning_rate": 0.0051068427873979475,
        "one_hot_max_size": 2,
        "random_strength": 0.6363393354045445,
    },
}
