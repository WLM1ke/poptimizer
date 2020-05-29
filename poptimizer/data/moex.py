"""Основные функции агрегации данных по котировкам акций."""
import functools
from concurrent import futures
from typing import Tuple, Optional, List

import numpy as np
import pandas as pd

from poptimizer import store
from poptimizer.store import SECURITIES, LOT_SIZE, INDEX, CLOSE, TURNOVER

__all__ = ["lot_size", "prices", "turnovers", "securities_with_reg_number", "index"]


def securities_with_reg_number() -> pd.Index:
    """Все ценные акции с регистрационным номером."""
    manager = store.Securities()
    df = manager[SECURITIES]
    return df.dropna(axis=0).index


def lot_size(tickers: Optional[Tuple[str, ...]] = None) -> pd.Series:
    """Информация о размере лотов для тикеров.

    :param tickers:
        Перечень тикеров, для которых нужна информация. При отсутствии информация будет предоставлена
        для всех торгуемых бумаг.
    :return:
        Информация о размере лотов.
    """
    manager = store.Securities()
    df = manager[SECURITIES]
    if tickers:
        df = df.loc[list(tickers)]
    return df[LOT_SIZE]


def index(last_date: pd.Timestamp) -> pd.DataFrame:
    """Загрузка данных по индексу полной доходности с учетом российских налогов - MCFTRR.

    :param last_date:
        Последняя дата котировок.
    :return:
        История цен закрытия индекса.
    """
    manager = store.Index()
    df = manager[INDEX]
    return df.loc[:last_date, CLOSE]


@functools.lru_cache(maxsize=1)
def quotes(tickers: Tuple[str, ...]) -> List[pd.DataFrame]:
    """Информация о котировках для заданных тикеров.

    :param tickers:
        Перечень тикеров, для которых нужна информация.
    :return:
        Список с котировками.
    """
    manager = store.Quotes()
    with futures.ThreadPoolExecutor() as executor:
        future_tickers = [
            executor.submit(lambda x: manager[x], ticker) for ticker in tickers
        ]
    return [future.result() for future in future_tickers]


@functools.lru_cache(maxsize=1)
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
    quotes_list = quotes(tickers)
    df = pd.concat(
        [
            df[CLOSE] if not df.empty else pd.DataFrame(columns=[CLOSE])
            for df in quotes_list
        ],
        axis=1,
    )
    df = df.loc[:last_date]
    df.columns = tickers
    return df.replace(to_replace=[np.nan, 0], method="ffill")


@functools.lru_cache(maxsize=1)
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
    quotes_list = quotes(tickers)
    df = pd.concat(
        [
            df[TURNOVER] if not df.empty else pd.DataFrame(columns=[TURNOVER])
            for df in quotes_list
        ],
        axis=1,
    )
    df = df.loc[:last_date]
    df.columns = tickers
    return df.fillna(0, axis=0)
