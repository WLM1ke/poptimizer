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


def _compare(source_name: str, df_local: pd.DataFrame, df_source: pd.DataFrame) -> pd.DataFrame:
    """Сравнивает данные по дивидендам из двух источников."""
    df = pd.concat([df_local, df_source], axis="columns")
    df.columns = ["LOCAL", "SOURCE"]
    df["STATUS"] = "ERROR"
    equal_div = np.isclose(df.iloc[:, 0], df.iloc[:, 1])
    df.loc[equal_div, "STATUS"] = ""

    print(f"\nСРАВНЕНИЕ ЛОКАЛЬНЫХ ДАННЫХ С {source_name}\n\n{df}")  # noqa: WPS421

    return df


def dividends_validation(ticker: str) -> None:
    """Проверяет корректности данных о дивидендах для тикера.

    Сравнивает основные данные по дивидендам с альтернативными источниками и распечатывает результаты
    сравнения.

    :param ticker:
        Тикер.
    """
    df_div = common.dividends_force_update(ticker)

    _compare("dohod.ru", df_div, common.dohod(ticker))
    _compare("conomy.ru", df_div, common.conomy(ticker))

    df = common.smart_lab()
    df = df.loc[df.index == ticker]
    _compare("smart-lab.ru", df_div, df.set_index(names.DATE))
