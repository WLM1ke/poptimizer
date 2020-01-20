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
pd.set_option("display.max_rows", 90)
pd.set_option("display.width", None)

# Путь к директории с отчетам
REPORTS_PATH = pathlib.Path(__file__).parents[1] / "reports"

# Путь к MongoDB и dump с данными по дивидендам
MONGO_PATH = pathlib.Path(__file__).parents[1] / "db"
MONGO_DUMP = pathlib.Path(__file__).parents[1] / "dump"

# Множитель, для переходя к после налоговым значениям
AFTER_TAX = 1 - 0.13

# Параметр для доверительных интервалов
T_SCORE = 2.0

# База дивидендов содержит данные с начала 2010 года
# Постепенно срок будет сдвигаться к началу режима TQBR для корректного учета сдвига T+2
STATS_START = pd.Timestamp("2010-08-01")

# Максимальный объем одной торговой операции в долях портфеля
MAX_TRADE = 1 / 100

# Параметры ML-модели
ML_PARAMS = {
    "data": (
        ("Label", {"days": 374, "div_share": 0.7, "on_off": True}),
        ("Scaler", {"days": 229, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 259, "on_off": True, "periods": 7}),
        ("DivYield", {"days": 249, "on_off": True, "periods": 1}),
        ("Mom1m", {"days": 27, "on_off": False}),
        ("RetMax", {"days": 41, "on_off": True}),
        ("ChMom6m", {"days": 115, "on_off": True}),
        ("STD", {"days": 30, "on_off": True}),
        ("DayOfYear", {"on_off": False}),
        ("TurnOver", {"days": 236, "normalize": True, "on_off": True}),
        ("TurnOverVar", {"days": 278, "on_off": True}),
    ),
    "model": {
        "bagging_temperature": 0.5294673570513457,
        "depth": 3,
        "l2_leaf_reg": 3.8686532475976176,
        "learning_rate": 0.0023365744126986306,
        "one_hot_max_size": 1000,
        "random_strength": 1.372153403040582,
    },
}
