from typing import Annotated

from pydantic import AfterValidator, Field

from poptimizer.domain import domain


class Row(domain.Row):
    day: domain.Day
    dividend: float = Field(gt=0)


class Dividends(domain.Entity):
    df: Annotated[
        list[Row],
        AfterValidator(domain.sorted_by_day_validator),
        AfterValidator(domain.after_start_date_validator),
    ] = Field(default_factory=list[Row])

    def update(self, update_day: domain.Day, rows: list[Row]) -> None:
        self.day = update_day
        self.df = rows
