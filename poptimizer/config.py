"""Основные настраиваемые параметры"""
import logging
import pandas as pd
import pathlib


class POptimizerError(Exception):
    """Базовое исключение."""


# Конфигурация логгера
logging.basicConfig(level=logging.INFO)

# Количество колонок в распечатках без переноса на несколько страниц
pd.set_option("display.max_columns", 20)
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
TURNOVER_CUT_OFF = 0.53 * MAX_TRADE

# Параметры ML-модели
LABEL_RANGE = [26, 64]
STD_RANGE = [134, 275]
MOM12M_RANGE = [250, 524]
DIVYIELD_RANGE = [240, 444]

ML_PARAMS = (
    (
        (True, {"days": 51}),
        (True, {"days": 243}),
        (True, {}),
        (True, {"days": 437}),
        (True, {"days": 382}),
    ),
    {
        "bagging_temperature": 0.6694389644638299,
        "depth": 6,
        "l2_leaf_reg": 0.9849409721664748,
        "learning_rate": 0.06450956340496615,
        "one_hot_max_size": 2,
        "random_strength": 1.494284431362221,
        "ignored_features": [],
    },
)
