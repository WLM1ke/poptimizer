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
TURNOVER_CUT_OFF = 4.8 * MAX_TRADE

# Параметры ML-модели
LABEL_RANGE = [30, 114]
STD_RANGE = [30, 114]
MOM12M_RANGE = [260, 572]
DIVYIELD_RANGE = [250, 514]
MOM1M_RANGE = [10, 20]
MIN1M_RANGE = [16, 25]

ML_PARAMS = (
    (
        (True, {"days": 63}),
        (True, {"days": 35}),
        (True, {}),
        (True, {"days": 355}),
        (True, {"days": 317}),
        (False, {"days": 14}),
        (True, {"days": 21}),
    ),
    {
        "bagging_temperature": 0.8838142096540308,
        "depth": 9,
        "l2_leaf_reg": 2.004507284599178,
        "learning_rate": 0.07549295345285609,
        "one_hot_max_size": 2,
        "random_strength": 1.3947327436006047,
        "ignored_features": [0, 2, 3],
    },
)
