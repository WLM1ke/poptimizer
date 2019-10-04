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

# Путь к MongoDB и dump с данными по дивидендам
MONGO_PATH = pathlib.Path(__file__).parents[1] / "db"
MONGO_DUMP = pathlib.Path(__file__).parents[1] / "dump"

# Множитель, для переходя к после налоговым значениям
AFTER_TAX = 1 - 0.13

# Параметр для доверительных интервалов
T_SCORE = 2.0

# База дивидендов содержит данные с начала 2010 года
# Постепенно срок будет сдвигаться к началу режима TQBR для корректного учета сдвига T+2
STATS_START = pd.Timestamp("2010-07-01")

# Максимальный объем одной торговой операции в долях портфеля
MAX_TRADE = 1 / 100

# Параметры ML-модели
ML_PARAMS = {
    "data": (
        ("Label", {"days": 142, "div_share": 0.3, "on_off": True}),
        ("Scaler", {"days": 209, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 201, "on_off": True, "periods": 1}),
        ("DivYield", {"days": 277, "on_off": True, "periods": 1}),
        ("Mom1m", {"days": 28, "on_off": False}),
        ("RetMax", {"days": 43, "on_off": True}),
        ("ChMom6m", {"days": 100, "on_off": True}),
        ("STD", {"days": 27, "on_off": True}),
        ("DayOfYear", {"on_off": False}),
        ("TurnOver", {"days": 230, "normalize": True, "on_off": True}),
    ),
    "model": {
        "bagging_temperature": 0.5999796112662071,
        "depth": 12,
        "l2_leaf_reg": 2.1599907061478696,
        "learning_rate": 0.00532201493155293,
        "one_hot_max_size": 1000,
        "random_strength": 1.3084110230689294,
    },
}
