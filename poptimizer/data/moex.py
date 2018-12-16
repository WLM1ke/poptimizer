"""Основные функции агрегации данных по котировкам акций."""
import asyncio
from typing import Tuple, Optional, List

import numpy as np
import pandas as pd

from poptimizer import store

__all__ = ["lot_size", "prices", "turnovers"]


async def _securities(tickers: Optional[Tuple[str, ...]] = None) -> pd.Series:
    """Информация о размере лотов для тикеров.

    :param tickers:
        Перечень тикеров, для которых нужна информация. При отсутствии информация будет предоставлена
        для всех торгуемых бумаг.
    :return:
        Информация о размере лотов.
    """
    async with store.Client() as client:
        db = client.securities()
        df = await db.get()
    if tickers:
        return df.loc[list(tickers), store.LOT_SIZE]
    return df[store.LOT_SIZE]


def lot_size(tickers: Optional[Tuple[str, ...]] = None) -> pd.Series:
    """Информация о размере лотов для тикеров.

    :param tickers:
        Перечень тикеров, для которых нужна информация. При отсутствии информация будет предоставлена
        для всех торгуемых бумаг.
    :return:
        Информация о размере лотов.
    """
    return asyncio.run(_securities(tickers))


async def _quotes(tickers: Tuple[str, ...]) -> List[pd.DataFrame]:
    """Информация о котировках для заданных тикеров (цена закрытия и объем).

    :param tickers:
        Перечень тикеров, для которых нужна информация.
    :return:
        Список с котировками.
    """
    async with store.Client() as client:
        db = client.quotes(tickers)
        return await db.get()


def prices(tickers: tuple, last_date: pd.Timestamp) -> pd.DataFrame:
    """Дневные цены закрытия для указанных тикеров до указанной даты включительно.

    Пропуски заполнены предыдущими значениями.

    :param tickers:
        Тикеры, для которых нужна информация.
    :param last_date:
        Последняя дата цен закрытия.
    :return:
        Цены закрытия.
    """
    quotes_list = asyncio.run(_quotes(tickers))
    df = pd.concat([df[store.CLOSE] for df in quotes_list], axis=1)
    df = df.loc[:last_date]
    df.columns = tickers
    return df.replace(to_replace=[np.nan, 0], method="ffill")


def turnovers(tickers: tuple, last_date: pd.Timestamp) -> pd.DataFrame:
    """Дневные обороты для указанных тикеров до указанной даты включительно.

    Пропуски заполнены нулевыми значениями.

    :param tickers:
        Тикеры, для которых нужна информация.
    :param last_date:
        Последняя дата оборотов.
    :return:
        Обороты.
    """
    quotes_list = asyncio.run(_quotes(tickers))
    df = pd.concat([df[store.TURNOVER] for df in quotes_list], axis=1)
    df = df.loc[:last_date]
    df.columns = tickers
    return df.fillna(0, axis=0)
