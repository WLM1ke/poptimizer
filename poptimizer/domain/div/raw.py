import bisect
import itertools
from datetime import date
from typing import Annotated

from pydantic import AfterValidator, Field, PositiveFloat

from poptimizer import errors
from poptimizer.domain import domain


class Row(domain.Row):
    day: domain.Day
    dividend: PositiveFloat

    def to_tuple(self) -> tuple[domain.Day, float]:
        return self.day, self.dividend


def _sorted_by_date_and_div(df: list[Row]) -> list[Row]:
    day_pairs = itertools.pairwise(row.to_tuple() for row in df)

    if not all(day <= next_ for day, next_ in day_pairs):
        raise ValueError("raw dividends are not sorted")

    return df


class DivRaw(domain.Entity):
    df: Annotated[
        list[Row],
        AfterValidator(_sorted_by_date_and_div),
        AfterValidator(domain.after_start_date_validator),
    ] = Field(default_factory=list[Row])

    def update(self, update_day: domain.Day, rows: list[Row]) -> None:
        self.day = update_day
        self.df = sorted(rows, key=lambda row: row.to_tuple())

    def add_row(self, row: Row) -> None:
        self.day = date.today()
        self.df.append(row)
        self.df = sorted(self.df, key=lambda row: row.to_tuple())

    def remove_row(self, row: Row) -> None:
        try:
            self.df.remove(row)
        except ValueError as err:
            raise errors.DomainError("dividend not found") from err

        self.day = date.today()

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
