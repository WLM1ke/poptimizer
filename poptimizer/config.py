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
pd.set_option("display.max_rows", 110)
pd.set_option("display.width", None)

# Путь к директории с отчетам
REPORTS_PATH = pathlib.Path(__file__).parents[1] / "reports"

# Путь к MongoDB и dump с данными по дивидендам
MONGO_PATH = pathlib.Path(__file__).parents[1] / "db"
MONGO_DUMP = pathlib.Path(__file__).parents[1] / "dump"

# Количество торговых дней в году
YEAR_IN_TRADING_DAYS = 12 * 21

# Множитель, для переходя к после налоговым значениям
AFTER_TAX = 1 - 0.13

# Параметр для доверительных интервалов
T_SCORE = 0.5

# База дивидендов содержит данные с начала 2010 года
# Постепенно срок будет сдвигаться к началу режима TQBR для корректного учета сдвига T+2
STATS_START = pd.Timestamp("2011-02-01")

# Максимальный объем одной торговой операции в долях портфеля
MAX_TRADE = 1 / 100

# Параметры ML-модели
ML_PARAMS = {
    "data": (
        ("Label", {"days": 147, "div_share": 0.1, "on_off": True}),
        ("Scaler", {"days": 149, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 197, "on_off": True, "periods": 2}),
        ("DivYield", {"days": 202, "on_off": True, "periods": 2}),
        ("Mom1m", {"days": 35, "on_off": True}),
        ("RetMax", {"days": 29, "on_off": True}),
        ("ChMom6m", {"days": 86, "on_off": True}),
        ("STD", {"days": 29, "on_off": True}),
        ("DayOfYear", {"on_off": True}),
        ("TurnOver", {"days": 252, "normalize": True, "on_off": True}),
        ("TurnOverVar", {"days": 125, "on_off": True}),
    ),
    "model": {
        "bagging_temperature": 1.2453010588045001,
        "depth": 7,
        "l2_leaf_reg": 0.8407137131776252,
        "learning_rate": 0.000554859970373293,
        "one_hot_max_size": 2,
        "random_strength": 1.1786264969298874,
    },
}
