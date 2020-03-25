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
        ("Label", {"days": 203, "div_share": 0.9, "on_off": True}),
        ("Scaler", {"days": 204, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 216, "on_off": True, "periods": 2}),
        ("DivYield", {"days": 193, "on_off": True, "periods": 4}),
        ("Mom1m", {"days": 30, "on_off": False}),
        ("RetMax", {"days": 38, "on_off": True}),
        ("ChMom6m", {"days": 134, "on_off": True}),
        ("STD", {"days": 33, "on_off": True}),
        ("DayOfYear", {"on_off": False}),
        ("TurnOver", {"days": 231, "normalize": True, "on_off": True}),
        ("TurnOverVar", {"days": 207, "on_off": True}),
    ),
    "model": {
        "bagging_temperature": 0.42640024246858915,
        "depth": 16,
        "l2_leaf_reg": 3.4340867549011183,
        "learning_rate": 0.005430304497114534,
        "one_hot_max_size": 1000,
        "random_strength": 1.1133165907537588,
    },
}
