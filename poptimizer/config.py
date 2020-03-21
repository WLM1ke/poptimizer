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

# Множитель, для переходя к после налоговым значениям
AFTER_TAX = 1 - 0.13

# Параметр для доверительных интервалов
T_SCORE = 2.0

# База дивидендов содержит данные с начала 2010 года
# Постепенно срок будет сдвигаться к началу режима TQBR для корректного учета сдвига T+2
STATS_START = pd.Timestamp("2010-10-01")

# Максимальный объем одной торговой операции в долях портфеля
MAX_TRADE = 1 / 100

# Параметры ML-модели
ML_PARAMS = {
    "data": (
        ("Label", {"days": 194, "div_share": 0.9, "on_off": True}),
        ("Scaler", {"days": 210, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 213, "on_off": True, "periods": 3}),
        ("DivYield", {"days": 201, "on_off": True, "periods": 3}),
        ("Mom1m", {"days": 33, "on_off": False}),
        ("RetMax", {"days": 38, "on_off": True}),
        ("ChMom6m", {"days": 131, "on_off": True}),
        ("STD", {"days": 34, "on_off": True}),
        ("DayOfYear", {"on_off": True}),
        ("TurnOver", {"days": 245, "normalize": False, "on_off": True}),
        ("TurnOverVar", {"days": 207, "on_off": True}),
    ),
    "model": {
        "bagging_temperature": 1.7729526391975787,
        "depth": 2,
        "l2_leaf_reg": 0.7986227785700475,
        "learning_rate": 0.010747572458327463,
        "one_hot_max_size": 2,
        "random_strength": 0.3845351869496457,
    },
}
