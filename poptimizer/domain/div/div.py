from pydantic import Field, field_validator

from poptimizer.domain import domain


class Row(domain.Row):
    day: domain.Day
    dividend: float = Field(gt=0)


class Dividends(domain.Entity):
    df: list[Row] = Field(default_factory=list[Row])

    def update(self, update_day: domain.Day, rows: list[Row]) -> None:
        self.day = update_day
        self.df = rows

    _must_be_sorted_by_date = field_validator("df")(domain.sorted_by_day_validator)
    _must_be_after_start_date = field_validator("df")(domain.after_start_date_validator)
