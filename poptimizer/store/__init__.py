"""Асинхронное локальное хранилище данных

Предоставляемые данные всегда актуальные - автоматически обновляются перед выдачей результата запроса.
Обновление осуществляется асинхронно, поэтому для ускорения целесообразно осуществлять сразу несколько
запросов.
"""
from poptimizer.store.client import Client, open_store
from poptimizer.store.cpi import Macro, CPI
from poptimizer.store.dividends import DIVIDENDS_START
from poptimizer.store.moex import Securities, Index, Quotes, SECURITIES, INDEX
from poptimizer.store.utils_new import (
    DATE,
    CLOSE,
    TURNOVER,
    TICKER,
    REG_NUMBER,
    LOT_SIZE,
    DIVIDENDS,
)
