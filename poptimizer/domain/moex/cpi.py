from datetime import date, timedelta
from typing import Final

from pydantic import Field, field_validator

from poptimizer import errors
from poptimizer.domain import domain

_MINIMUM_MONTHLY_CPI: Final = 0.99


class Row(domain.Row):
    day: domain.Day
    cpi: float = Field(gt=_MINIMUM_MONTHLY_CPI)

    @field_validator("day")
    def _must_be_last_day_of_month(cls, date: date) -> date:
        if (date + timedelta(days=1)).month == date.month:
            raise ValueError("not last day of the month")

        return date


class CPI(domain.Entity):
    df: list[Row] = Field(default_factory=list[Row])

    def update(self, update_day: domain.Day, rows: list[Row]) -> None:
        self.day = update_day

        if self.df != rows[: len(self.df)]:
            raise errors.DomainError("data mismatch error")

        self.df = rows

    _must_be_sorted_by_date = field_validator("df")(domain.sorted_by_day_validator)
