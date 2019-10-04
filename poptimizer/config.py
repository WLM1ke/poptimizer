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
STATS_START = pd.Timestamp("2010-06-01")

# Максимальный объем одной торговой операции в долях портфеля
MAX_TRADE = 1 / 100

# Параметры ML-модели
ML_PARAMS = {
    "data": (
        ("Label", {"days": 111, "div_share": 0.3, "on_off": True}),
        ("Scaler", {"days": 220, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 187, "on_off": True, "periods": 1}),
        ("DivYield", {"days": 256, "on_off": True, "periods": 1}),
        ("Mom1m", {"days": 32, "on_off": True}),
        ("RetMax", {"days": 48, "on_off": True}),
        ("ChMom6m", {"days": 97, "on_off": True}),
        ("STD", {"days": 24, "on_off": True}),
        ("DayOfYear", {"on_off": False}),
        ("TurnOver", {"days": 242, "normalize": False, "on_off": True}),
    ),
    "model": {
        "bagging_temperature": 0.7086647045742429,
        "depth": 14,
        "l2_leaf_reg": 1.6621105324472478,
        "learning_rate": 0.0037710058578652875,
        "one_hot_max_size": 1000,
        "random_strength": 1.8447224379576972,
    },
}
