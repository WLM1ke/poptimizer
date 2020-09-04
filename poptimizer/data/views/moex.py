"""Функции предоставления данных по котировкам акций."""
import functools
from typing import Tuple

import numpy as np
import pandas as pd
from pandas.tseries import offsets

from poptimizer.data.config import bootstrap
from poptimizer.data.ports import base, col
from poptimizer.data.views import crop


def last_history_date() -> pd.Timestamp:
    """Последняя доступная дата исторических котировок."""
    table_name = base.TableName(base.TRADING_DATES, base.TRADING_DATES)
    requests_handler = bootstrap.get_handler()
    df = requests_handler.get_df(table_name)
    return pd.Timestamp(df.loc[0, "till"])


def securities_with_reg_number() -> pd.Index:
    """Все акции с регистрационным номером."""
    table_name = base.TableName(base.SECURITIES, base.SECURITIES)
    requests_handler = bootstrap.get_handler()
    df = requests_handler.get_df(table_name)
    return df.dropna(axis=0).index


def lot_size(tickers: Tuple[str, ...]) -> pd.Series:
    """Информация о размере лотов для тикеров.

    :param tickers:
        Перечень тикеров, для которых нужна информация.
    :return:
        Информация о размере лотов.
    """
    table_name = base.TableName(base.SECURITIES, base.SECURITIES)
    requests_handler = bootstrap.get_handler()
    df = requests_handler.get_df(table_name)
    return df.loc[list(tickers), col.LOT_SIZE]


@functools.lru_cache(maxsize=1)
def prices(tickers: Tuple[str, ...], last_date: pd.Timestamp) -> pd.DataFrame:
    """Дневные цены закрытия для указанных тикеров до указанной даты включительно.

    Пропуски заполнены предыдущими значениями.

    :param tickers:
        Тикеры, для которых нужна информация.
    :param last_date:
        Последняя дата цен закрытия.
    :return:
        Цены закрытия.
    """
    quotes_list = crop.quotes(tickers)
    df = pd.concat(
        [df[col.CLOSE] for df in quotes_list],
        axis=1,
    )
    df = df.loc[:last_date]
    df.columns = tickers
    return df.replace(to_replace=[np.nan, 0], method="ffill")


@functools.lru_cache(maxsize=1)
def turnovers(tickers: Tuple[str, ...], last_date: pd.Timestamp) -> pd.DataFrame:
    """Дневные обороты для указанных тикеров до указанной даты включительно.

    Пропуски заполнены нулевыми значениями.

    :param tickers:
        Тикеры, для которых нужна информация.
    :param last_date:
        Последняя дата оборотов.
    :return:
        Обороты.
    """
    quotes_list = crop.quotes(tickers)
    df = pd.concat(
        [df[col.TURNOVER] for df in quotes_list],
        axis=1,
    )
    df = df.loc[:last_date]
    df.columns = tickers
    return df.fillna(0, axis=0)


def _dividends_all(tickers: Tuple[str, ...]) -> pd.DataFrame:
    """Дивиденды по заданным тикерам после уплаты налогов.

    Значения для дат, в которые нет дивидендов у данного тикера (есть у какого-то другого),
    заполняются 0.

    :param tickers:
        Тикеры, для которых нужна информация.
    :return:
        Дивиденды.
    """
    dfs = [crop.dividends(ticker) for ticker in tickers]
    df = pd.concat(dfs, axis=1)
    df = df.reindex(columns=tickers)
    df = df.fillna(0, axis=0)
    return df.mul(bootstrap.get_after_tax_rate())


def _t2_shift(date: pd.Timestamp, index: pd.DatetimeIndex) -> pd.Timestamp:
    """Рассчитывает эксдивидендную дату для режима T-2 на основании даты закрытия реестра.

    Если дата не содержится в индексе цен, то необходимо найти предыдущую из индекса цен. После этого
    взять сдвинутую на 1 назад дату.

    Если дата находится в будущем за пределом истории котировок, то нужно сдвинуть на 1 бизнес день
    вперед и на два назад. Это не эквивалентно сдвигу на один день назад для выходных.
    """
    if date <= index[-1]:
        position = index.get_loc(date, "ffill")
        return index[position - 1]

    next_b_day = date + offsets.BDay()
    return next_b_day - 2 * offsets.BDay()


def div_and_prices(
    tickers: Tuple[str, ...],
    last_date: pd.Timestamp,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Дивиденды на с привязкой к эксдивидендной дате и цены.

    Дивиденды на эксдивидендную дату нужны для корректного расчета доходности. Также для многих
    расчетов удобна привязка к торговым дням, а отсечки часто приходятся на выходные.

    Данные обрезаются с учетом установки о начале статистики.
    """
    price = prices(tickers, last_date)
    div = _dividends_all(tickers)
    div.index = div.index.map(functools.partial(_t2_shift, index=price.index))
    # Может образоваться несколько одинаковых дат, если часть дивидендов приходится на выходные
    div = div.groupby(by=col.DATE).sum()
    return div.reindex(index=price.index, fill_value=0), price
