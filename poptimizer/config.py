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
T_SCORE = 1.6

# База дивидендов содержит данные с начала 2010 года
# Постепенно срок будет сдвигаться к началу режима TQBR для корректного учета сдвига T+2
STATS_START = pd.Timestamp("2010-11-01")

# Максимальный объем одной торговой операции в долях портфеля
MAX_TRADE = 1 / 100

# Параметры ML-модели
ML_PARAMS = {
    "data": (
        ("Label", {"days": 203, "div_share": 0.8, "on_off": True}),
        ("Scaler", {"days": 225, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 193, "on_off": True, "periods": 2}),
        ("DivYield", {"days": 192, "on_off": True, "periods": 4}),
        ("Mom1m", {"days": 25, "on_off": False}),
        ("RetMax", {"days": 45, "on_off": True}),
        ("ChMom6m", {"days": 123, "on_off": True}),
        ("STD", {"days": 32, "on_off": True}),
        ("DayOfYear", {"on_off": True}),
        ("TurnOver", {"days": 236, "normalize": True, "on_off": True}),
        ("TurnOverVar", {"days": 199, "on_off": True}),
    ),
    "model": {
        "bagging_temperature": 0.8131692814075397,
        "depth": 15,
        "l2_leaf_reg": 1.1290080818753965,
        "learning_rate": 0.014342683407716387,
        "one_hot_max_size": 1000,
        "random_strength": 0.9548458820717005,
    },
}
