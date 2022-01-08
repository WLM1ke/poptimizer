"""Функции предоставления данных о котировках."""
import functools

import numpy as np
import pandas as pd
from pandas.tseries import offsets

from poptimizer.data.views.crop import div, not_div
from poptimizer.shared import col


@functools.lru_cache(maxsize=4)
def prices(
    tickers: tuple[str, ...],
    last_date: pd.Timestamp,
    price_type: col.PriceType = col.CLOSE,
) -> pd.DataFrame:
    """Дневные цены закрытия для указанных тикеров до указанной даты включительно.

    Пропуски заполнены предыдущими значениями.

    :param tickers:
        Тикеры, для которых нужна информация.
    :param last_date:
        Последняя дата цен закрытия.
    :param price_type:
        Тип цены — по умолчанию цена закрытия.
    :return:
        Цены закрытия.
    """
    df = _prices(tickers, price_type)
    df = df.loc[:last_date]
    df.columns = tickers

    return df.replace(to_replace=[np.nan, 0], method="ffill")


def _prices(tickers: tuple[str, ...], price_type: col.PriceType = col.CLOSE) -> pd.DataFrame:
    quotes_list = not_div.quotes(tickers)

    return pd.concat(
        [df[price_type] for df in quotes_list],
        axis=1,
    )


@functools.lru_cache(maxsize=1)
def turnovers(tickers: tuple[str, ...], last_date: pd.Timestamp) -> pd.DataFrame:
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
    tickers: tuple[str, ...],
    last_date: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Дивиденды с привязкой к эксдивидендной дате и цены.

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
