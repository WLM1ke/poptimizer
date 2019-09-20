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
pd.set_option("display.max_rows", 80)
pd.set_option("display.width", None)

# Путь к директории с отчетам
REPORTS_PATH = pathlib.Path(__file__).parents[1] / "reports"

# Путь к MongoDB
MONGO_PATH = pathlib.Path(__file__).parents[1] / "db"

# Множитель, для переходя к после налоговым значениям
AFTER_TAX = 1 - 0.13

# Параметр для доверительных интервалов
T_SCORE = 2.0

# Максимальный объем одной торговой операции в долях портфеля
MAX_TRADE = 1 / 100

# Период в торговых днях, за который медианный оборот торгов
TURNOVER_PERIOD = 54

# Минимальный оборот - преимущества акции снижаются при приближении медианного оборота к данному уровню
TURNOVER_CUT_OFF = 1 / 30

# База дивидендов содержит данные с начала 2010 года
# Постепенно срок будет сдвигаться к началу режима TQBR для корректного учета сдвига T+2
STATS_START = pd.Timestamp("2010-03-01")

# Параметры ML-модели
ML_PARAMS = {
    "data": (
        ("Label", {"days": 79, "div_share": 0.3, "on_off": True}),
        ("Scaler", {"days": 225, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 178, "on_off": True, "periods": 2}),
        ("DivYield", {"days": 239, "on_off": True, "periods": 1}),
        ("Mom1m", {"days": 41, "on_off": False}),
        ("RetMax", {"days": 54, "on_off": True}),
        ("ChMom6m", {"days": 90, "on_off": True}),
        ("STD", {"days": 27, "on_off": True}),
        ("DayOfYear", {"on_off": False}),
    ),
    "model": {
        "bagging_temperature": 0.8741295882011074,
        "depth": 13,
        "l2_leaf_reg": 1.4138240966644873,
        "learning_rate": 0.005390648531709855,
        "one_hot_max_size": 1000,
        "random_strength": 1.44386445646246,
    },
}
