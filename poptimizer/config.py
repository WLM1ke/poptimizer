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
        ("Label", {"days": 199, "div_share": 0.8, "on_off": True}),
        ("Scaler", {"days": 296, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 209, "on_off": True, "periods": 1}),
        ("DivYield", {"days": 171, "on_off": True, "periods": 6}),
        ("Mom1m", {"days": 27, "on_off": True}),
        ("RetMax", {"days": 43, "on_off": True}),
        ("ChMom6m", {"days": 129, "on_off": True}),
        ("STD", {"days": 32, "on_off": True}),
        ("DayOfYear", {"on_off": True}),
        ("TurnOver", {"days": 259, "normalize": False, "on_off": True}),
        ("TurnOverVar", {"days": 186, "on_off": True}),
    ),
    "model": {
        "bagging_temperature": 1.5336920050419836,
        "depth": 7,
        "l2_leaf_reg": 3.974553178597452,
        "learning_rate": 0.0038324340590848768,
        "one_hot_max_size": 1000,
        "random_strength": 1.297972607948483,
    },
}
