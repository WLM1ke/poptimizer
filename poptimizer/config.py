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
LABEL_RANGE = [27, 74]
STD_RANGE = [134, 275]
MOM12M_RANGE = [250, 524]
DIVYIELD_RANGE = [240, 444]
MOM1M_RANGE = [16, 21]

ML_PARAMS = (
    (
        (True, {"days": 62}),
        (True, {"days": 157}),
        (True, {}),
        (True, {"days": 375}),
        (True, {"days": 362}),
        (True, {"days": 19}),
    ),
    {
        "bagging_temperature": 0.7273263327047061,
        "depth": 7,
        "l2_leaf_reg": 0.8206118720234131,
        "learning_rate": 0.0519251093560293,
        "one_hot_max_size": 100,
        "random_strength": 0.8424283529004852,
        "ignored_features": [],
    },
)
