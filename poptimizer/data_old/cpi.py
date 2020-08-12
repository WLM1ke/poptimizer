"""Данные индексу потребительских цен."""
import pandas as pd

from poptimizer import store
from poptimizer.store import CPI


def monthly_cpi(date: pd.Timestamp) -> pd.Series:
    """Месячные данные индексу потребительских до указанной даты.

    :param date:
        Последняя дата.
    :return:
        Месячная инфляция.
    """
    manager = store.Macro()
    df = manager[CPI]
    return df.loc[:date, CPI]
