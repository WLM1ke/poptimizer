"""Проверка статуса актуальности данных по дивидендам."""
from typing import Tuple, List

import numpy as np
import pandas as pd

from poptimizer import store
from poptimizer.config import AFTER_TAX, STATS_START
from poptimizer.data import div
from poptimizer.store import TICKER, DIVIDENDS, SMART_LAB

__all__ = ["smart_lab_status", "dividends_status"]


def smart_lab() -> pd.DataFrame:
    """Информация о ближайших дивидендах на https://www.smart-lab.ru"""
    manager = store.SmartLab()
    return manager[SMART_LAB]


def smart_lab_status(tickers: Tuple[str, ...]):
    """Печатает информацию об актуальности данных в локальной базе дивидендов.

    :param tickers:
        Тикеры, для которых нужно проверить актуальность данных.
    """
    web = smart_lab()
    local = div.dividends_all(tuple(set(web[TICKER].values))) / AFTER_TAX
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


def _get_div_data(ticker: str) -> List[Tuple[str, pd.DataFrame]]:
    """Информация о дивидендах из основной базы и альтернативных источников."""
    data_sources = [
        (store.Dividends(), ticker),
        (store.Dohod(), ticker),
        (store.Conomy(), ticker),
        (store.SmartLab(), SMART_LAB),
    ]
    rez = []
    for mng, item in data_sources:
        name = mng.__class__.__name__
        try:
            df = mng[item]
        except Exception as error:
            df = error
        rez.append((name, df))
    return rez


def dividends_status(ticker: str):
    """Проверяет необходимость обновления данных для тикера.

    Сравнивает основные данные по дивидендам с альтернативными источниками и распечатывает результаты
    сравнения.

    :param ticker:
        Тикер.
    """
    dfs = _get_div_data(ticker)
    _, main_df = dfs[0]
    main_df = main_df.loc[main_df.index >= pd.Timestamp(STATS_START), ticker]

    result = []
    for name, df in dfs[1:]:
        print(f"\nСРАВНЕНИЕ ОСНОВНЫХ ДАННЫХ С {name}\n")
        if isinstance(df, Exception):
            print(df)
            result.append(df)
            continue
        if name != "SmartLab":
            df = df.loc[df.index >= pd.Timestamp(STATS_START), ticker]
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
