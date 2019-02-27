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
TURNOVER_CUT_OFF = 4.1 * MAX_TRADE

# Параметры ML-модели
LABEL_RANGE = [30, 114]
STD_RANGE = [115, 274]
MOM12M_RANGE = [260, 572]
DIVYIELD_RANGE = [250, 514]
MOM1M_RANGE = [10, 20]
MIN1M_RANGE = [16, 23]

ML_PARAMS = (
    (
        (True, {"days": 96}),
        (False, {"days": 243}),
        (False, {}),
        (True, {"days": 376}),
        (True, {"days": 440}),
        (True, {"days": 12}),
        (False, {"days": 19}),
    ),
    {
        "bagging_temperature": 1.3536330310501257,
        "depth": 8,
        "l2_leaf_reg": 3.1708654061275174,
        "learning_rate": 0.08431563722615622,
        "one_hot_max_size": 100,
        "random_strength": 1.0748330052735107,
        "ignored_features": [0, 1, 5],
    },
)
