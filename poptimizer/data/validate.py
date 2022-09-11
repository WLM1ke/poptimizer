"""Валидаторы для таблиц."""
import itertools
from datetime import datetime
from typing import Protocol


class _RowWithDate(Protocol):
    date: datetime


def sorted_by_date(df: list[_RowWithDate]) -> list[_RowWithDate]:
    """Валидирует сортировку списка по полю даты по возрастанию."""
    dates_pairs = itertools.pairwise(row.date for row in df)

    if not all(date < next_ for date, next_ in dates_pairs):
        raise ValueError("dates are not sorted")

    return df
