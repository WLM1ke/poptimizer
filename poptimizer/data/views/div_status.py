"""Информация об актуальности данных по дивидендам."""
import math
from datetime import datetime
from typing import Callable, Final

import pandas as pd

from poptimizer.data import ports
from poptimizer.data.app import bootstrap, viewers
from poptimizer.data.domain import events
from poptimizer.data.views.crop import div

# Точность сравнения дивидендов
from poptimizer.shared import col

RET_TOL: Final = 2e-3

DivSource = Callable[[str], pd.DataFrame]


def _new_div_all(viewer: viewers.Viewer = bootstrap.VIEWER) -> pd.DataFrame:
    """Информация по дивидендам с smart-lab.ru."""
    raw_data = viewer.get_df(ports.DIV_NEW, ports.DIV_NEW)
    indexed = raw_data.set_index(col.DATE, append=True)
    grouped = indexed.groupby(level=[0, 1]).sum(min_count=1)
    return grouped.reset_index(level=1)


def _check_div_in_df(
    ticker: str,
    date: datetime,
    div_value: float,
    df: pd.DataFrame,
) -> bool:
    """Проверка наличия дивидендов в DataFrame.

    Должна присутствовать дата и значение для не NaN дивидендов.
    """
    if date not in df.index:
        return False

    if math.isnan(div_value):
        return True

    rel_tol = RET_TOL * 4

    return math.isclose(df.loc[date, ticker], div_value, rel_tol=rel_tol)


def new_dividends(tickers: tuple[str, ...]) -> set[str]:
    """Список тикеров с новой информацией о дивидендах.

    По российским акция используется информация о предстоящих дивидендах со SmartLab, а по иностранным с
    MOEX.

    Выбираются только тикеры из предоставленного списка.

    :param tickers:
        Тикеры, для которых нужно проверить актуальность данных.
    :return:
        Список новых тикеров.
    """
    status = set()
    for ticker, date, div_value in _new_div_all().itertuples():
        if ticker not in tickers:
            continue

        df = div.dividends(ticker)
        if not _check_div_in_df(ticker, date, div_value, df):
            status.add(ticker)

    if status:
        print("\nДАННЫЕ ПО ДИВИДЕНДАМ ТРЕБУЮТ ОБНОВЛЕНИЯ\n")  # noqa: WPS421
        print(", ".join(status))  # noqa: WPS421

    return status


def _row_comp(row: pd.Series, rel_tol: float = RET_TOL) -> bool:
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


def dividends_validation(ticker: str) -> pd.DataFrame:
    """Проверяет корректности данных о дивидендах для тикера.

    Запускает принудительное обновление, сравнивает основные данные по дивидендам с альтернативными
    источниками и распечатывает результаты.
    """
    command = events.UpdateDivCommand(ticker)
    bootstrap.BUS.handle_event(command)

    df_local = div.dividends(ticker)
    df_local.columns = ["LOCAL"]

    div_ex = div.div_ext(ticker)

    df_comp = _compare(div_ex.iloc[:, -1:], df_local)
    df_comp = pd.concat(
        [div_ex.iloc[:, :-1], df_comp],
        axis=1,
    )

    comp_str = f"\nСравнение интернет источников с локальными данными - {ticker}\n\n{df_comp}"
    print(comp_str)  # noqa: WPS421

    return df_comp
