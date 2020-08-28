"""Информация о актуальности данных по дивидендам."""
from typing import List, Tuple

import numpy as np
import pandas as pd

from poptimizer.data import names
from poptimizer.data.views import common


def new_on_smart_lab(tickers: Tuple[str, ...]) -> List[str]:
    """Список тикеров с новой информацией о дивидендах на SmartLab.

    Выбираются только тикеры из предоставленного списка.

    :param tickers:
        Тикеры, для которых нужно проверить актуальность данных.
    :return:
        Список новых тикеров.
    """
    status = []
    for ticker, date, div in common.smart_lab().itertuples():
        if ticker not in tickers:
            continue

        df = common.dividends(ticker)
        if date not in df.index:
            status.append(ticker)
        elif not np.isclose(df.loc[date, ticker], div):
            status.append(ticker)

    if status:
        print("\nДАННЫЕ ПО ДИВИДЕНДАМ ТРЕБУЮТ ОБНОВЛЕНИЯ\n")  # noqa: WPS421
        print(", ".join(status))  # noqa: WPS421

    return status


def _compare(source_name: str, df_div: pd.DataFrame, df_dohod: pd.DataFrame) -> pd.DataFrame:
    """Сравнивает данные по дивидендам из двух источников."""
    df = pd.concat([df_div, df_dohod], axis=1)
    df.columns = ["LOCAL", "SOURCE"]
    df["STATUS"] = "ERROR"
    equal_div = np.isclose(df.iloc[:, 0], df.iloc[:, 1])
    df.loc[equal_div, "STATUS"] = ""

    print(f"\nСРАВНЕНИЕ ЛОКАЛЬНЫХ ДАННЫХ С {source_name}\n\n{df}")  # noqa: WPS421

    return df
