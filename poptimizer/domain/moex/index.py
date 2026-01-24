from datetime import date
from typing import Annotated, Final

from pydantic import AfterValidator, Field

from poptimizer import errors
from poptimizer.domain import domain

RVI: Final = domain.UID("RVI")
IMOEX2: Final = domain.UID("IMOEX2")
MCF2TRR: Final = domain.UID("MCF2TRR")
RUGBITR1Y: Final = domain.UID("RUGBITR1Y")
INDEXES: Final = {
    MCF2TRR: domain.UID("MCFTRR"),
    domain.UID("MEFNTRR"): None,
    domain.UID("MEMMTRR"): None,
    domain.UID("MEOGTRR"): None,
    domain.UID("MESMTRR"): None,
    IMOEX2: domain.UID("IMOEX"),
    RVI: None,
    RUGBITR1Y: None,
    domain.UID("RUGBITR10Y"): None,
    domain.UID("RUCBITRL3"): None,
    domain.UID("MREDC"): None,
    domain.UID("RTSUSDCUR"): None,
}


class Row(domain.Row):
    day: domain.Day = Field(alias="begin")
    close: float = Field(alias="close", gt=0)


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
