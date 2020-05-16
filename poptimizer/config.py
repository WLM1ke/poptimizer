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
        ("Label", {"days": 144, "div_share": 0.2, "on_off": True}),
        ("Scaler", {"days": 164, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 184, "on_off": True, "periods": 1}),
        ("DivYield", {"days": 210, "on_off": True, "periods": 3}),
        ("Mom1m", {"days": 33, "on_off": True}),
        ("RetMax", {"days": 31, "on_off": True}),
        ("ChMom6m", {"days": 86, "on_off": True}),
        ("STD", {"days": 27, "on_off": True}),
        ("DayOfYear", {"on_off": False}),
        ("TurnOver", {"days": 250, "normalize": False, "on_off": True}),
        ("TurnOverVar", {"days": 133, "on_off": True}),
    ),
    "model": {
        "bagging_temperature": 0.8131008495942844,
        "depth": 1,
        "l2_leaf_reg": 0.49813611958834125,
        "learning_rate": 0.0012187452259781145,
        "one_hot_max_size": 1000,
        "random_strength": 1.5040045895191374,
    },
}
