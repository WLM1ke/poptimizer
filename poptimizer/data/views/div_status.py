"""Информация о актуальности данных по дивидендам."""
import math
from typing import Callable, Final, List, Tuple

import pandas as pd

from poptimizer.data.config import bootstrap
from poptimizer.data.ports import outer
from poptimizer.data_di.shared import col
from poptimizer.data.views.crop import div

# Точность сравнения дивидендов
RET_TOL: Final = 1e-3

DivSource = Callable[[str], pd.DataFrame]


def _smart_lab_all() -> pd.DataFrame:
    """Информация по дивидендам с smart-lab.ru."""
    table_name = outer.TableName(outer.SMART_LAB, outer.SMART_LAB)
    requests_handler = bootstrap.get_handler()
    return requests_handler.get_df(table_name)


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


def smart_lab(ticker: str) -> pd.Series:
    """Возвращает данные со SmartLab для определенного тикера."""
    df = _smart_lab_all()
    df = df.loc[df.index == ticker]
    df = df.set_index(col.DATE)
    df.columns = [ticker]
    return df


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


def dividends_validation(
    ticker: str,
    sources: Tuple[DivSource, ...] = (div.dohod, div.conomy, div.bcs, smart_lab),
) -> None:
    """Проверяет корректности данных о дивидендах для тикера.

    Сравнивает основные данные по дивидендам с альтернативными источниками и распечатывает результаты
    """
    dfs = pd.concat([func(ticker) for func in sources], axis=1)
    dfs.columns = [func.__name__ for func in sources]
    dfs.index = dfs.index.astype("datetime64[ns]")

    median = dfs.median(axis=1)
    median.name = "MEDIAN"

    df_local = div.dividends(ticker, force_update=True)
    df_local.columns = ["LOCAL"]

    df_comp = _compare(median, df_local)

    df_comp = pd.concat([dfs, df_comp], axis=1)

    comp_str = f"\nСравнение интернет источников с локальными данными - {ticker}\n\n{df_comp}"
    print(comp_str)  # noqa: WPS421
