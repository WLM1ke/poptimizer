"""Информация для отчетов."""
import pandas as pd

from poptimizer.data.views import crop


def cpi(date: pd.Timestamp) -> pd.Series:
    """Потребительская инфляция."""
    df = crop.cpi()
    return df.loc[:date]


def index(last_date: pd.Timestamp) -> pd.DataFrame:
    """Загрузка данных по индексу полной доходности с учетом российских налогов - MCFTRR.

    :param last_date:
        Последняя дата котировок.
    :return:
        История цен закрытия индекса.
    """
    df = crop.index()
    return df.loc[:last_date]
