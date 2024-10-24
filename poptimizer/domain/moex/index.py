from datetime import date

from pydantic import Field, field_validator

from poptimizer import errors
from poptimizer.domain import domain


class Row(domain.Row):
    day: domain.Day = Field(alias="TRADEDATE")
    close: float = Field(alias="CLOSE", gt=0)


class Index(domain.Entity):
    df: list[Row] = Field(default_factory=list[Row])

    def update(self, update_day: domain.Day, rows: list[Row]) -> None:
        self.day = update_day

        if not self.df:
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

    _must_be_sorted_by_date = field_validator("df")(domain.sorted_by_day_validator)
