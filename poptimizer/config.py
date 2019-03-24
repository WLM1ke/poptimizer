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
MAX_TRADE = 0.013

# Период в торговых днях, за который медианный оборот торгов
TURNOVER_PERIOD = 21

# Минимальный оборот - преимущества акции снижаются при приближении медианного оборота к данному уровню
TURNOVER_CUT_OFF = 4.5 * MAX_TRADE

# Параметры ML-модели
ML_PARAMS = {
    "data": (
        ("Label", {"days": 30, "on_off": True}),
        ("STD", {"days": 18, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 240, "on_off": True}),
        ("DivYield", {"days": 278, "on_off": True}),
        ("Mom1m", {"days": 24, "on_off": True}),
        ("RetMax", {"days": 30, "on_off": True}),
    ),
    "model": {
        "bagging_temperature": 1.4442236395066252,
        "depth": 7,
        "l2_leaf_reg": 3.965071053664432,
        "learning_rate": 0.01200925851468165,
        "one_hot_max_size": 100,
        "random_strength": 0.8619376437714823,
    },
}
