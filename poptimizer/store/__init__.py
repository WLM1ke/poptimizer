"""Асинхронное локальное хранилище данных

Предоставляемые данные всегда актуальные - автоматически обновляются перед выдачей результата запроса.
Обновление осуществляется асинхронно, поэтому для ускорения целесообразно осуществлять сразу несколько
запросов.
"""
from poptimizer.store.client import Client
from poptimizer.store.dividends import DIVIDENDS_START
from poptimizer.store.utils import (
    CLOSE,
    TURNOVER,
    LOT_SIZE,
    TICKER,
    DATE,
    REG_NUMBER,
    DIVIDENDS,
)
