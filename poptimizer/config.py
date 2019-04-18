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
TURNOVER_CUT_OFF = 4.3 * MAX_TRADE

# Параметры ML-модели
ML_PARAMS = {
    "data": (
        ("Label", {"days": 39, "on_off": True}),
        ("STD", {"days": 22, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 252, "on_off": True}),
        ("DivYield", {"days": 293, "on_off": True, "periods": 1}),
        ("Mom1m", {"days": 30, "on_off": True}),
        ("RetMax", {"days": 31, "on_off": True}),
    ),
    "model": {
        "bagging_temperature": 0.46678436655457123,
        "depth": 8,
        "l2_leaf_reg": 1.7381056485420951,
        "learning_rate": 0.0026968585999663924,
        "one_hot_max_size": 2,
        "random_strength": 0.9961129082017114,
    },
}
