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
TURNOVER_CUT_OFF = 1.5 * MAX_TRADE

# Параметры ML-модели
LABEL_RANGE = [30, 114]
STD_RANGE = [115, 274]
MOM12M_RANGE = [260, 572]
DIVYIELD_RANGE = [240, 444]
MOM1M_RANGE = [11, 20]

ML_PARAMS = (
    (
        (True, {"days": 95}),
        (True, {"days": 247}),
        (False, {}),
        (True, {"days": 477}),
        (True, {"days": 312}),
        (True, {"days": 13}),
    ),
    {
        "bagging_temperature": 0.5874582767026979,
        "depth": 7,
        "l2_leaf_reg": 3.5822771482737363,
        "learning_rate": 0.05899499435294281,
        "one_hot_max_size": 100,
        "random_strength": 1.282227613377058,
        "ignored_features": [],
    },
)
