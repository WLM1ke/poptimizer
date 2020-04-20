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
pd.set_option("display.max_rows", 100)
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
T_SCORE = 1.4

# База дивидендов содержит данные с начала 2010 года
# Постепенно срок будет сдвигаться к началу режима TQBR для корректного учета сдвига T+2
STATS_START = pd.Timestamp("2010-11-01")

# Максимальный объем одной торговой операции в долях портфеля
MAX_TRADE = 1 / 100

# Параметры ML-модели
ML_PARAMS = {
    "data": (
        ("Label", {"days": 211, "div_share": 0.8, "on_off": True}),
        ("Scaler", {"days": 205, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 173, "on_off": True, "periods": 2}),
        ("DivYield", {"days": 207, "on_off": True, "periods": 5}),
        ("Mom1m", {"days": 25, "on_off": False}),
        ("RetMax", {"days": 42, "on_off": True}),
        ("ChMom6m", {"days": 117, "on_off": True}),
        ("STD", {"days": 31, "on_off": True}),
        ("DayOfYear", {"on_off": False}),
        ("TurnOver", {"days": 260, "normalize": True, "on_off": True}),
        ("TurnOverVar", {"days": 188, "on_off": True}),
    ),
    "model": {
        "bagging_temperature": 1.652284803722443,
        "depth": 15,
        "l2_leaf_reg": 2.1921695430037627,
        "learning_rate": 0.007496675181901148,
        "one_hot_max_size": 1000,
        "random_strength": 0.39725818988335576,
    },
}
