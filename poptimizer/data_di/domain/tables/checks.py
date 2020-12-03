"""Проверки для индексов и данных после обновления."""
import pandas as pd

from poptimizer.data_di.domain.tables import base
from poptimizer.shared import domain


def unique_increasing_index(df: pd.DataFrame) -> None:
    """Тестирует индекс на уникальность и возрастание."""
    index = df.index
    if not index.is_monotonic_increasing:
        raise base.TableIndexError("Индекс не возрастающий")
    if not index.is_unique:
        raise base.TableIndexError("Индекс не уникальный")


def df_data(id_: domain.ID, df_old: pd.DataFrame, df_new: pd.DataFrame) -> None:
    """Сравнивает новые данные со старыми для старого индекса."""
    if df_old is None:
        return

    df_new_val = df_new.reindex(df_old.index)
    try:
        pd.testing.assert_frame_equal(df_new_val, df_old, check_dtype=False)
    except AssertionError:
        raise base.TableNewDataMismatchError(id_)
