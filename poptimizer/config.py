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
STATS_START = pd.Timestamp("2011-02-01")

# Максимальный объем одной торговой операции в долях портфеля
MAX_TRADE = 1 / 100

# Параметры ML-модели
ML_PARAMS = {
    "data": (
        ("Label", {"days": 151, "div_share": 0.3, "on_off": True}),
        ("Scaler", {"days": 164, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 184, "on_off": True, "periods": 1}),
        ("DivYield", {"days": 211, "on_off": True, "periods": 2}),
        ("Mom1m", {"days": 32, "on_off": True}),
        ("RetMax", {"days": 33, "on_off": True}),
        ("ChMom6m", {"days": 88, "on_off": True}),
        ("STD", {"days": 30, "on_off": True}),
        ("DayOfYear", {"on_off": True}),
        ("TurnOver", {"days": 270, "normalize": True, "on_off": True}),
        ("TurnOverVar", {"days": 147, "on_off": True}),
    ),
    "model": {
        "bagging_temperature": 2.4793556010442694,
        "depth": 4,
        "l2_leaf_reg": 0.46009538650415005,
        "learning_rate": 0.0018100226481827053,
        "one_hot_max_size": 1000,
        "random_strength": 0.47964627127098,
    },
}
