"""Информация о актуальности данных по дивидендам."""
import math
from typing import Callable, Final

import pandas as pd

from poptimizer.data import ports
from poptimizer.data.app import bootstrap, viewers
from poptimizer.data.domain import events
from poptimizer.data.views.crop import div

# Точность сравнения дивидендов
RET_TOL: Final = 1e-3

DivSource = Callable[[str], pd.DataFrame]


def _smart_lab_all(viewer: viewers.Viewer = bootstrap.VIEWER) -> pd.DataFrame:
    """Информация по дивидендам с smart-lab.ru."""
    return viewer.get_df(ports.DIV_NEW, ports.DIV_NEW)


def new_on_smart_lab(tickers: tuple[str, ...]) -> list[str]:
    """Список тикеров с новой информацией о дивидендах на SmartLab.

    Выбираются только тикеры из предоставленного списка.

    :param tickers:
        Тикеры, для которых нужно проверить актуальность данных.
    :return:
        Список новых тикеров.
    """
    status = set()
    for ticker, date, div_value in _smart_lab_all().itertuples():
        if ticker not in tickers:
            continue

        df = div.dividends(ticker)
        if date not in df.index:
            status.add(ticker)
        elif not math.isclose(df.loc[date, ticker], div_value, rel_tol=RET_TOL):
            status.add(ticker)

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
