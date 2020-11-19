"""Информация о актуальности данных по дивидендам."""
import math
from typing import Callable, Final, List, Tuple

import pandas as pd

from poptimizer.data.views.crop import div
from poptimizer.data_di.app import bootstrap, viewers
from poptimizer.data_di.domain.tables import base
from poptimizer.data_di.shared import col

# Точность сравнения дивидендов
RET_TOL: Final = 1e-3

DivSource = Callable[[str], pd.DataFrame]


def _smart_lab_all(viewer: viewers.Viewer = bootstrap.VIEWER) -> pd.DataFrame:
    """Информация по дивидендам с smart-lab.ru."""
    return viewer.get_df(base.SMART_LAB, base.SMART_LAB)


def new_on_smart_lab(tickers: Tuple[str, ...]) -> List[str]:
    """Список тикеров с новой информацией о дивидендах на SmartLab.

    Выбираются только тикеры из предоставленного списка.

    :param tickers:
        Тикеры, для которых нужно проверить актуальность данных.
    :return:
        Список новых тикеров.
    """
    status = []
    for ticker, date, div_value in _smart_lab_all().itertuples():
        if ticker not in tickers:
            continue

        df = div.dividends(ticker)
        if date not in df.index:
            status.append(ticker)
        elif not math.isclose(df.loc[date, ticker], div_value, rel_tol=RET_TOL):
            status.append(ticker)

    if status:
        print("\nДАННЫЕ ПО ДИВИДЕНДАМ ТРЕБУЮТ ОБНОВЛЕНИЯ\n")  # noqa: WPS421
        print(", ".join(status))  # noqa: WPS421

    return status


def _row_comp(row: pd.Series, rel_tol: float = 1e-3) -> bool:
    """Сравнение двух значений дивидендов."""
    return math.isclose(row.iloc[0], row.iloc[1], rel_tol=rel_tol)


def _compare(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    """Сравнивает данные по дивидендам из двух источников."""
    df = pd.concat([df1, df2], axis="columns")
    df["STATUS"] = "ERROR"

    if not df.empty:
        equal_div = df.apply(_row_comp, axis=1)
        df.loc[equal_div, "STATUS"] = ""

    return df


def dividends_validation(ticker: str) -> None:
    """Проверяет корректности данных о дивидендах для тикера.

    Сравнивает основные данные по дивидендам с альтернативными источниками и распечатывает результаты.
    """
    div_ex = div.div_ext(ticker)

    df_local = div.dividends(ticker, force_update=True)
    df_local.columns = ["LOCAL"]

    df_comp = _compare(div_ex.iloc[:, -1:], df_local)
    df_comp = pd.concat([div_ex.iloc[:, :-1], df_comp], axis=1)

    comp_str = f"\nСравнение интернет источников с локальными данными - {ticker}\n\n{df_comp}"
    print(comp_str)  # noqa: WPS421
