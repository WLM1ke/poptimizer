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
        ("Label", {"days": 351, "div_share": 0.7, "on_off": True}),
        ("Scaler", {"days": 216, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 272, "on_off": True, "periods": 6}),
        ("DivYield", {"days": 260, "on_off": True, "periods": 1}),
        ("Mom1m", {"days": 27, "on_off": False}),
        ("RetMax", {"days": 44, "on_off": True}),
        ("ChMom6m", {"days": 106, "on_off": True}),
        ("STD", {"days": 29, "on_off": True}),
        ("DayOfYear", {"on_off": False}),
        ("TurnOver", {"days": 237, "normalize": False, "on_off": True}),
        ("TurnOverVar", {"days": 286, "on_off": True}),
    ),
    "model": {
        "bagging_temperature": 1.090783759214851,
        "depth": 10,
        "l2_leaf_reg": 1.3907836082762675,
        "learning_rate": 0.0028413358812555043,
        "one_hot_max_size": 1000,
        "random_strength": 1.852974754022738,
    },
}
