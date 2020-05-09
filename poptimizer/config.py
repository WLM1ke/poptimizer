"""Основные настраиваемые параметры"""
import logging
import pathlib

import pandas as pd
import torch


class POptimizerError(Exception):
    """Базовое исключение."""


# Воспроизводиломость https://pytorch.org/docs/stable/notes/randomness.html
torch.manual_seed(0)

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
STATS_START = pd.Timestamp("2011-01-01")

# Максимальный объем одной торговой операции в долях портфеля
MAX_TRADE = 1 / 100

# Параметры ML-модели
ML_PARAMS = {
    "data": (
        ("Label", {"days": 143, "div_share": 0.4, "on_off": True}),
        ("Scaler", {"days": 161, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 175, "on_off": True, "periods": 1}),
        ("DivYield", {"days": 192, "on_off": True, "periods": 3}),
        ("Mom1m", {"days": 29, "on_off": True}),
        ("RetMax", {"days": 35, "on_off": True}),
        ("ChMom6m", {"days": 98, "on_off": True}),
        ("STD", {"days": 28, "on_off": True}),
        ("DayOfYear", {"on_off": False}),
        ("TurnOver", {"days": 268, "normalize": False, "on_off": True}),
        ("TurnOverVar", {"days": 163, "on_off": True}),
    ),
    "model": {
        "bagging_temperature": 0.4521894117626858,
        "depth": 4,
        "l2_leaf_reg": 3.545172783263082,
        "learning_rate": 0.003349473217292303,
        "one_hot_max_size": 1000,
        "random_strength": 0.8612212169197176,
    },
}
