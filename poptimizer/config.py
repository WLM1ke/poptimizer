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
        ("Label", {"days": 409, "div_share": 0.7, "on_off": True}),
        ("Scaler", {"days": 221, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 268, "on_off": True, "periods": 8}),
        ("DivYield", {"days": 255, "on_off": True, "periods": 1}),
        ("Mom1m", {"days": 30, "on_off": True}),
        ("RetMax", {"days": 36, "on_off": True}),
        ("ChMom6m", {"days": 123, "on_off": True}),
        ("STD", {"days": 28, "on_off": True}),
        ("DayOfYear", {"on_off": False}),
        ("TurnOver", {"days": 256, "normalize": False, "on_off": True}),
        ("TurnOverVar", {"days": 287, "on_off": True}),
    ),
    "model": {
        "bagging_temperature": 0.7770049899416437,
        "depth": 5,
        "l2_leaf_reg": 4.325227983446653,
        "learning_rate": 0.0034048837807904766,
        "one_hot_max_size": 1000,
        "random_strength": 1.8393983169840653,
    },
}
