"""Проверка статуса актуальности данных по дивидендам."""
import asyncio
from typing import Tuple

import numpy as np
import pandas as pd

from poptimizer import store
from poptimizer.config import AFTER_TAX
from poptimizer.data import div
from poptimizer.store import TICKER, DIVIDENDS


async def _smart_lab() -> pd.DataFrame:
    """Информация о ближайших дивидендах на https://www.smart-lab.ru"""
    async with store.Client() as client:
        db = client.smart_lab()
        return await db.get()


def smart_lab(tickers: Tuple[str, ...]):
    """Печатает информацию об актуальности данных в локальной базе дивидендов.

    :param tickers:
        Тикеры, для которых нужно проверить актуальность данных.
    """
    web = asyncio.run(_smart_lab())
    local = div.dividends_all(tuple(web[TICKER].values)) / AFTER_TAX
    status = ([], [])
    for i in range(len(web)):
        date = web.index[i]
        ticker = web.iloc[i][TICKER]
        value = web.iloc[i][DIVIDENDS]
        if (date not in local.index) or not np.isclose(local.loc[date, ticker], value):
            if ticker in tickers:
                status[0].append(ticker)
            else:
                status[1].append(ticker)
    if status[0]:
        print("\nДАННЫЕ ПО ДИВИДЕНДАМ ТРЕБУЮТ ОБНОВЛЕНИЯ", "\n")
        print(", ".join(status[0]))
    if status[1]:
        print("\nВ БАЗУ ДАННЫХ ДИВИДЕНДОВ МОЖНО ДОБАВИТЬ", "\n")
        print(", ".join(status[1]))


if __name__ == "__main__":
    smart_lab(("PHOR", "AKRN"))
