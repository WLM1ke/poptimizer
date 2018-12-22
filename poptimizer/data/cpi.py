"""Данные индексу потребительских цен."""
import asyncio

import pandas as pd

from poptimizer import store


async def _cpi() -> pd.Series:
    """Месячные данные индексу потребительских цен."""
    async with store.Client() as client:
        db = client.cpi()
        df = await db.get()
    return df


def monthly_cpi(date: pd.Timestamp) -> pd.Series:
    """Месячные данные индексу потребительских до указанной даты.

    :param date:
        Последняя дата.
    :return:
        Месячная инфляция.
    """
    df = asyncio.run(_cpi())
    return df[:date]
