import bisect
import itertools

from pydantic import Field, field_validator

from poptimizer.domain import domain


class Row(domain.Row):
    day: domain.Day
    dividend: float = Field(gt=0)

    def to_tuple(self) -> tuple[domain.Day, float]:
        return self.day, self.dividend


class DivRaw(domain.Entity):
    df: list[Row] = Field(default_factory=list[Row])

    def update(self, update_day: domain.Day, rows: list[Row]) -> None:
        self.day = update_day

        rows.sort(key=lambda row: row.to_tuple())

        self.df = rows

    def has_day(self, day: domain.Day) -> bool:
        pos = bisect.bisect_left(self.df, day, key=lambda row: row.day)

        return pos != len(self.df) and self.df[pos].day == day

    def has_row(self, row: Row) -> bool:
        pos = bisect.bisect_left(
            self.df,
            row.to_tuple(),
            key=lambda row: row.to_tuple(),
        )

        return pos != len(self.df) and row == self.df[pos]

    @field_validator("df")
    def _sorted_by_date_and_div(cls, df: list[Row]) -> list[Row]:
        day_pairs = itertools.pairwise(row.to_tuple() for row in df)

        if not all(day <= next_ for day, next_ in day_pairs):
            raise ValueError("raw dividends are not sorted")

        return df
