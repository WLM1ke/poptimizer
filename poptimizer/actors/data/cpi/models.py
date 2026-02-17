from datetime import date, timedelta
from typing import Annotated, Final

from pydantic import AfterValidator, Field, field_validator

from poptimizer.core import domain

_MINIMUM_MONTHLY_CPI: Final = 0.99


class CPIRow(domain.Row):
    day: domain.Day
    cpi: float = Field(gt=_MINIMUM_MONTHLY_CPI)

    @field_validator("day")
    def _must_be_last_day_of_month(cls, date: date) -> date:
        if (date + timedelta(days=1)).month == date.month:
            raise ValueError("not last day of the month")

        return date


class CPI(domain.Entity):
    df: Annotated[
        list[CPIRow],
        AfterValidator(domain.sorted_by_day_validator),
    ] = Field(default_factory=list[CPIRow])

    def update(self, rows: list[CPIRow]) -> None:
        self.df = rows
