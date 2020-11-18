"""Функции предоставления данных по котировкам акций."""
import functools
from typing import Tuple

import numpy as np
import pandas as pd
from pandas.tseries import offsets

from poptimizer.data.views.crop import div, not_div
from poptimizer.data_di.app import bootstrap, viewers
from poptimizer.data_di.domain.tables import base
from poptimizer.data_di.shared import col


def last_history_date(viewer: viewers.Viewer = bootstrap.VIEWER) -> pd.Timestamp:
    """Последняя доступная дата исторических котировок."""
    df = viewer.get_df(base.TRADING_DATES, base.TRADING_DATES)
    return df.loc[0, "till"]


def securities(viewer: viewers.Viewer = bootstrap.VIEWER) -> pd.Index:
    """Все акции."""
    df = viewer.get_df(base.SECURITIES, base.SECURITIES)
    return df.index


def lot_size(tickers: Tuple[str, ...], viewer: viewers.Viewer = bootstrap.VIEWER) -> pd.Series:
    """Информация о размере лотов для тикеров."""
    df = viewer.get_df(base.SECURITIES, base.SECURITIES)
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
    quotes_list = not_div.quotes(tickers)
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
    quotes_list = not_div.quotes(tickers)
    df = pd.concat(
        [df[col.TURNOVER] for df in quotes_list],
        axis=1,
    )
    df = df.loc[:last_date]
    df.columns = tickers
    return df.fillna(0, axis=0)


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
    div_data = div.dividends_all(tickers)
    div_data.index = div_data.index.map(functools.partial(_t2_shift, index=price.index))
    # Может образоваться несколько одинаковых дат, если часть дивидендов приходится на выходные
    div_data = div_data.groupby(by=lambda date: date).sum()
    return div_data.reindex(index=price.index, fill_value=0), price
