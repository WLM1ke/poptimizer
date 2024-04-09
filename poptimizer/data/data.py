import itertools
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from poptimizer.core import consts, domain


class LastUpdate(domain.State):
    day: domain.Day = consts.START_DAY


class Row(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class _RowWithDate(Protocol):
    day: domain.Day


def sorted_by_day_validator(df: list[_RowWithDate]) -> list[_RowWithDate]:
    dates_pairs = itertools.pairwise(row.day for row in df)

    if not all(day < next_ for day, next_ in dates_pairs):
        raise ValueError("df not sorted by day")

    return df


def after_start_date_validator(df: list[_RowWithDate]) -> list[_RowWithDate]:
    if df and (day := df[0].day) < consts.START_DAY:
        raise ValueError(f"day before start day {day}")

    return df
