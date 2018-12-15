"""Агрегация данных по дивидендам."""
import asyncio
import functools
from typing import Tuple, List

import numpy as np
import pandas as pd
from pandas.tseries import offsets

from poptimizer import store
from poptimizer.config import AFTER_TAX
from poptimizer.data import moex
from poptimizer.store import DATE

__all__ = ["log_total_returns", "dividends"]


async def _dividends(tickers: Tuple[str, ...]) -> List[pd.DataFrame]:
    """Информация о дивидендах для заданных тикеров.

    :param tickers:
        Перечень тикеров, для которых нужна информация.
    :return:
        Список с дивидендами.
    """
    async with store.Client() as client:
        db = client.dividends(tickers)
        return await db.get()


def dividends_all(tickers: tuple) -> pd.DataFrame:
    """Дивиденды по заданным тикерам после уплаты налогов.

    Значения для дат, в которые нет дивидендов у данного тикера (есть у какого-то другого),
    заполняются 0.

    :param tickers:
        Тикеры, для которых нужна информация.
    :return:
        Дивиденды.
    """
    quotes_list = asyncio.run(_dividends(tickers))
    df = pd.concat([df for df in quotes_list], axis=1)
    return df.fillna(0, axis=0) * AFTER_TAX


def dividends(tickers: tuple, last_date: pd.Timestamp) -> pd.DataFrame:
    """Дивиденды по заданным тикерам до указанной даты после уплаты налогов.

    Значения для дат, в которые нет дивидендов у данного тикера (есть у какого-то другого),
    заполняются 0.

    :param tickers:
        Тикеры, для которых нужна информация.
    :param last_date:
        Последняя дата.
    :return:
        Дивиденды.
    """
    return dividends_all(tickers).loc[:last_date]


def t2_shift(date: pd.Timestamp, index: pd.DatetimeIndex):
    """Рассчитывает эксдивидендную дату для режима T-2 на основании даты закрытия реестра.

    Если дата не содержится в индексе цен, то необходимо найти предыдущую из индекса цен. После этого
    взять сдвинутую на 1 назад дату. Если дата находится в будущем за пределом истории котировок, то
    достаточно сдвинуть на 1 бизнес день назад - упрощенный подход, который может не корректно работать
    из-за праздников.
    """
    if date <= index[-1]:
        position = index.get_loc(date, "ffill")
        return index[position - 1]
    # Часть дивидендов приходится на выходной, поэтому нельзя просто сдвинуться на один бизнес день назад
    # Сначала двигаемся на следующий бизнес день, а потом на два бизнес дня назад
    next_b_day = date + offsets.BDay()
    return next_b_day - 2 * offsets.BDay()


def log_total_returns(tickers: tuple, last_date: pd.Timestamp) -> pd.DataFrame:
    """Логарифмы дневных доходностей с учетом посленалоговых дивидендов.

    :param tickers:
        Тикеры, для которых нужна информация.
    :param last_date:
        Последняя дата цен закрытия.
    :return:
        Логарифмы полных дневных доходностей.
    """
    p1 = moex.prices(tickers, last_date)
    p0 = p1.shift(1)
    div = dividends_all(tickers)
    div.index = div.index.map(functools.partial(t2_shift, index=p1.index))
    # Может образоваться несколько дат, если часть дивидендов приходится на выходные
    div = div.groupby(by=DATE).sum()
    div = div.loc[:last_date]
    returns = p1.add(div, fill_value=0) / p0
    return returns.iloc[1:].apply(np.log)
