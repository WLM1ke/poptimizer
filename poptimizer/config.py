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
pd.set_option("display.max_rows", 80)
pd.set_option("display.width", None)

# Путь к директории с данными
DATA_PATH = pathlib.Path(__file__).parents[1] / "data"

# Путь к директории с отчетам
REPORTS_PATH = pathlib.Path(__file__).parents[1] / "reports"

# Конфигурация MongoDB
MONGO_PATH = pathlib.Path(__file__).parents[1] / "db"

# Множитель, для переходя к после налоговым значениям
AFTER_TAX = 1 - 0.13

# Параметр для доверительных интервалов
T_SCORE = 2.0

# Максимальный объем одной торговой операции в долях портфеля
MAX_TRADE = 0.01

# Период в торговых днях, за который медианный оборот торгов
TURNOVER_PERIOD = 84

# Минимальный оборот - преимущества акции снижаются при приближении медианного оборота к данному уровню
TURNOVER_CUT_OFF = 1 / 30

# База дивидендов содержит данные с начала 2010 года
# Постепенно срок будет сдвигаться к началу режима TQBR для корректного учета сдвига T+2
STATS_START = pd.Timestamp("2010-02-01")

# Параметры ML-модели
ML_PARAMS = {
    "data": (
        ("Label", {"days": 73, "div_share": 0.2, "on_off": True}),
        ("Scaler", {"days": 224, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 184, "on_off": True, "periods": 2}),
        ("DivYield", {"days": 256, "on_off": True, "periods": 1}),
        ("Mom1m", {"days": 42, "on_off": True}),
        ("RetMax", {"days": 54, "on_off": True}),
        ("ChMom6m", {"days": 96, "on_off": True}),
        ("STD", {"days": 25, "on_off": True}),
        ("DayOfYear", {"on_off": False}),
    ),
    "model": {
        "bagging_temperature": 0.9472314292149879,
        "depth": 16,
        "l2_leaf_reg": 1.459514552976774,
        "learning_rate": 0.006744415354565958,
        "one_hot_max_size": 2,
        "random_strength": 0.4618058090309339,
    },
}
