from datetime import date, timedelta
from typing import Annotated, Final, Protocol

from pydantic import AfterValidator, Field, field_validator

from poptimizer.core import domain, fsm

_MINIMUM_MONTHLY_CPI: Final = 0.99


class Row(domain.Row):
    day: domain.Day
    cpi: float = Field(gt=_MINIMUM_MONTHLY_CPI)

    @field_validator("day")
    def _must_be_last_day_of_month(cls, date: date) -> date:
        if (date + timedelta(days=1)).month == date.month:
            raise ValueError("not last day of the month")

        return date


class CPI(domain.Entity):
    df: Annotated[
        list[Row],
        AfterValidator(domain.sorted_by_day_validator),
    ] = Field(default_factory=list[Row])

    def update(self, rows: list[Row]) -> None:
        self.df = rows


class Client(Protocol):
    async def get_cpi(self) -> list[Row]: ...


async def update(ctx: fsm.CoreCtx, web_client: Client) -> None:
    table = await ctx.get_for_update(CPI)

    row = await web_client.get_cpi()

    table.update(row)
