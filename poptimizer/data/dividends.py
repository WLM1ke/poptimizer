"""Агрегация данных по дивидендам."""
import asyncio
from typing import Tuple, List

import pandas as pd

from poptimizer import store


async def dividends_list(tickers: Tuple[str]) -> List[pd.DataFrame]:
    """Информация о дивидендах для заданных тикеров.

    :param tickers:
        Перечень тикеров, для которых нужна информация.
    :return:
        Список с дивидендами.
    """
    async with store.Client() as client:
        db = client.dividends(tickers)
        return await db.get()


def dividends(tickers: tuple, last_date: pd.Timestamp) -> pd.DataFrame:
    """Дивиденды по заданным тикерам до указанной даты.

    Значения для дат, в которые нет дивидендов у данного тикера (есть у какого-то другого),
    заполняются 0.

    :param tickers:
        Тикеры, для которых нужна информация.
    :param last_date:
        Последняя дата.
    :return:
        Дивиденды.
    """
    quotes_list = asyncio.run(dividends_list(tickers))
    df = pd.concat([df for df in quotes_list], axis=1)
    df = df.loc[:last_date]
    return df.fillna(0, axis=0)
