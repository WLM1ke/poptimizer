from typing import Annotated

from pydantic import AfterValidator, Field, PositiveFloat

from poptimizer.core import domain


class Row(domain.Row):
    day: domain.Day
    dividend: PositiveFloat


class Dividends(domain.Entity):
    df: Annotated[
        list[Row],
        AfterValidator(domain.sorted_by_day_validator),
        AfterValidator(domain.after_start_date_validator),
    ] = Field(default_factory=list[Row])

    def update(self, rows: list[Row]) -> None:
        self.df = rows
