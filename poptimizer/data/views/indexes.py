"""Индексы потребительских цен и MOEX."""
import pandas as pd

from poptimizer.data.views import crop


def cpi(date: pd.Timestamp) -> pd.Series:
    """Потребительская инфляция."""
    df = crop.cpi()
    return df.loc[:date]


def mcftrr(last_date: pd.Timestamp) -> pd.Series:
    """Загрузка данных по индексу полной доходности с учетом российских налогов - MCFTRR.

    :param last_date:
        Последняя дата котировок.
    :return:
        История цен закрытия индекса.
    """
    df = crop.index()
    return df.loc[:last_date]


def rvi(last_date: pd.Timestamp) -> pd.Series:
    """Индекс волатильности RVI."""
    df = crop.index("RVI")
    return df.loc[:last_date]
