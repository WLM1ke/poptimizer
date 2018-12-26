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
TURNOVER_CUT_OFF = 0.16 * MAX_TRADE

# Параметры данных и модели
ML_PARAMS = (
    (
        (True, {"days": 58}),
        (True, {"days": 217}),
        (False, {}),
        (True, {"days": 259}),
        (True, {"days": 305}),
    ),
    {
        "bagging_temperature": 1.0045160722070197,
        "depth": 6,
        "l2_leaf_reg": 1.4602225401115263,
        "learning_rate": 0.06666969456431047,
        "one_hot_max_size": 2,
        "random_strength": 1.2136752554436034,
        "ignored_features": [1],
    },
)
