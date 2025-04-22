from datetime import date
from typing import Annotated, Final

from pydantic import AfterValidator, Field

from poptimizer import errors
from poptimizer.domain import domain

RVI: Final = domain.UID("RVI")
IMOEX: Final = domain.UID("IMOEX")
MCFTRR: Final = domain.UID("MCFTRR")
RUGBITR1Y: Final = domain.UID("RUGBITR1Y")
INDEXES: Final = (
    MCFTRR,
    domain.UID("MEOGTRR"),
    IMOEX,
    RVI,
    RUGBITR1Y,
)


class Row(domain.Row):
    day: domain.Day = Field(alias="TRADEDATE")
    close: float = Field(alias="CLOSE", gt=0)


class Index(domain.Entity):
    df: Annotated[
        list[Row],
        AfterValidator(domain.sorted_by_day_validator),
    ] = Field(default_factory=list[Row])

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
