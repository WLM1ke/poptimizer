"""Проверка статуса актуальности данных по дивидендам."""
import asyncio
from typing import Tuple

import numpy as np
import pandas as pd

from poptimizer import store
from poptimizer.config import AFTER_TAX
from poptimizer.data import div
from poptimizer.store import TICKER, DIVIDENDS, DIVIDENDS_START

__all__ = ["smart_lab_status", "dividends_status"]


async def _smart_lab() -> pd.DataFrame:
    """Информация о ближайших дивидендах на https://www.smart-lab.ru"""
    async with store.Client() as client:
        db = client.smart_lab()
        return await db.get()


def smart_lab() -> pd.DataFrame:
    """Информация о ближайших дивидендах на https://www.smart-lab.ru"""
    return asyncio.run(_smart_lab())


def smart_lab_status(tickers: Tuple[str, ...]):
    """Печатает информацию об актуальности данных в локальной базе дивидендов.

    :param tickers:
        Тикеры, для которых нужно проверить актуальность данных.
    """
    web = smart_lab()
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


async def _gather_div_data(ticker: str):
    """Информация о дивидендах из основной базы и альтернативных источников."""
    async with store.Client() as client:
        await client.dividends(ticker).create(ticker)
        data_sources = [
            client.dividends(ticker),
            client.dohod(ticker),
            client.conomy(ticker),
            client.smart_lab(),
        ]
        names = [i.__class__.__name__ for i in data_sources]
        aws = [i.get() for i in data_sources]
        dfs = await asyncio.gather(*aws)
        return list(zip(names, dfs))


def dividends_status(ticker: str):
    """Проверяет необходимость обновления данных для тикера.

    Сравнивает основные данные по дивидендам с альтернативными источниками и распечатывает результаты
    сравнения.

    :param ticker:
        Тикер.
    """
    dfs = asyncio.run(_gather_div_data(ticker))
    _, main_df = dfs[0]

    result = []
    for name, df in dfs[1:]:
        print(f"\nСРАВНЕНИЕ ОСНОВНЫХ ДАННЫХ С {name}\n")
        if name != "SmartLab":
            df = df[df.index >= pd.Timestamp(DIVIDENDS_START)]
        else:
            df = df[df[TICKER] == ticker][DIVIDENDS]
        df.name = name
        compare_df = pd.concat([main_df, df], axis="columns")
        compare_df["STATUS"] = "ERROR"
        compare_df.loc[
            np.isclose(compare_df[ticker].values, compare_df[name].values), "STATUS"
        ] = ""
        print(compare_df)
        result.append(compare_df)
    return result
