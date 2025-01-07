from datetime import date
from typing import Annotated

from pydantic import AfterValidator, Field

from poptimizer import errors
from poptimizer.domain import domain


class Row(domain.Row):
    day: domain.Day = Field(alias="begin")
    open: float = Field(alias="open", gt=0)
    close: float = Field(alias="close", gt=0)
    high: float = Field(alias="high", gt=0)
    low: float = Field(alias="low", gt=0)
    turnover: float = Field(alias="value", ge=0)


class Quotes(domain.Entity):
    df: Annotated[
        list[Row],
        AfterValidator(domain.sorted_by_day_validator),
        AfterValidator(domain.after_start_date_validator),
    ] = Field(default_factory=list[Row])

    def update(self, update_day: domain.Day, rows: list[Row]) -> None:
        self.day = update_day

        if not self.df:
            rows.sort(key=lambda row: row.day)
            self.df = rows

            return

        last = self.df[-1]

        if last != (first := rows[0]):
            raise errors.DomainError(f"{self.uid} data mismatch {last} vs {first}")

        self.df.extend(rows[1:])

    def last_row_date(self) -> date | None:
        if not self.df:
            return None

        return self.df[-1].day
