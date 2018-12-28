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
        (True, {"days": 195}),
        (False, {}),
        (True, {"days": 282}),
        (True, {"days": 332}),
    ),
    {
        "bagging_temperature": 0.9388504407881838,
        "depth": 5,
        "l2_leaf_reg": 3.2947929042414654,
        "learning_rate": 0.07663371920281654,
        "one_hot_max_size": 100,
        "random_strength": 0.9261064363697566,
        "ignored_features": [1],
    },
)
