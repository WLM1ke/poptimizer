"""Индексы потребительских цен и MOEX."""
import pandas as pd

from poptimizer.data.views.crop import not_div


def cpi(date: pd.Timestamp) -> pd.Series:
    """Потребительская инфляция."""
    df = not_div.cpi()
    return df.loc[:date]


def mcftrr(last_date: pd.Timestamp) -> pd.Series:
    """Загрузка данных по индексу полной доходности с учетом российских налогов - MCFTRR.

    :param last_date:
        Последняя дата котировок.
    :return:
        История цен закрытия индекса.
    """
    df = not_div.index()
    return df.loc[:last_date]


def imoex(last_date: pd.Timestamp) -> pd.Series:
    """Загрузка данных по основному индексу MOEX - IMOEX.

    :param last_date:
        Последняя дата котировок.
    :return:
        История цен закрытия индекса.
    """
    df = not_div.index("IMOEX")
    return df.loc[:last_date]


def rvi(last_date: pd.Timestamp) -> pd.Series:
    """Индекс волатильности RVI."""
    df = not_div.index("RVI")
    return df.loc[:last_date]


def index(ticker: str, last_date: pd.Timestamp) -> pd.Series:
    """Поучение произвольного индекса из загружаемых."""
    df = not_div.index(ticker)
    return df.loc[:last_date]


def usd(last_date: pd.Timestamp) -> pd.Series:
    """Курс доллара."""
    df = not_div.usd()
    return df.loc[:last_date]
