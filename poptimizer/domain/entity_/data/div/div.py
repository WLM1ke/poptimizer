from pydantic import Field, field_validator

from poptimizer.domain.entity_ import entity


class Row(entity.Row):
    day: entity.Day
    dividend: float = Field(gt=0)


class Dividends(entity.Entity):
    df: list[Row] = Field(default_factory=list[Row])

    def update(self, update_day: entity.Day, rows: list[Row]) -> None:
        self.day = update_day
        self.df = rows

    _must_be_sorted_by_date = field_validator("df")(entity.sorted_by_day_validator)
    _must_be_after_start_date = field_validator("df")(entity.after_start_date_validator)
