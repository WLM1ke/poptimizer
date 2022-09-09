"""Сервис ручного ввода дивидендов."""
import bisect
from datetime import datetime
from typing import ClassVar

from pydantic import Field, validator

from poptimizer.data import domain, validate


class Raw(domain.Row):
    """Информация о дивидендах с указанием валюты."""

    date: datetime
    dividend: float
    currency: domain.Currency


class Table(domain.Table):
    """Таблица дивидендов с указанием валюты."""

    group: ClassVar[domain.Group] = domain.Group.RAW_DIV
    df: list[Raw] = Field(default_factory=list[Raw])

    def update(self, update_day: datetime) -> None:
        """Обновляет таблицу."""

    def has_date(self, date: datetime) -> bool:
        """Проверяет, есть ли в таблице указанная дата."""
        df = self.df
        pos = bisect.bisect_left(df, date, key=lambda row: row.date)

        return pos != len(df) and df[pos].date == date

    _must_be_sorted_by_date = validator("df", allow_reuse=True)(validate.sorted_by_date_non_unique)
