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
LABEL_RANGE = [27, 74]
STD_RANGE = [134, 275]
MOM12M_RANGE = [250, 524]
DIVYIELD_RANGE = [240, 444]
MOM1M_RANGE = [16, 21]

ML_PARAMS = (
    (
        (True, {"days": 62}),
        (True, {"days": 224}),
        (False, {}),
        (True, {"days": 354}),
        (True, {"days": 338}),
        (False, {"days": 17}),
    ),
    {
        "bagging_temperature": 1.0507261727126722,
        "depth": 1,
        "l2_leaf_reg": 3.003154246930572,
        "learning_rate": 0.07465451244262414,
        "one_hot_max_size": 100,
        "random_strength": 1.0831540755123423,
        "ignored_features": [1, 4],
    },
)
