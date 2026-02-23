from typing import Annotated, Protocol

from pydantic import AfterValidator, Field

from poptimizer.core import actors, domain, errors


class Row(domain.Row):
    day: domain.Day = Field(alias="begin")
    open: float = Field(alias="open", gt=0)
    close: float = Field(alias="close", gt=0)
    high: float = Field(alias="high", gt=0)
    low: float = Field(alias="low", gt=0)
    turnover: float = Field(alias="value", gt=0)


class USD(domain.Entity):
    df: Annotated[
        list[Row],
        AfterValidator(domain.sorted_by_day_validator),
    ] = Field(default_factory=list[Row])

    def update(self, rows: list[Row]) -> None:
        if not self.df:
            self.df = rows

            return

        last = self.df[-1]

        if last != (first := rows[0]):
            raise errors.DomainError(f"{self.uid} data mismatch {last} vs {first}")

        self.df.extend(rows[1:])

    def last_row_date(self) -> domain.Day | None:
        if not self.df:
            return None

        return self.df[-1].day


class Client(Protocol):
    async def get_usd(
        self,
        start_day: domain.Day | None,
        end_day: domain.Day,
    ) -> list[Row]: ...


async def update(ctx: actors.CoreCtx, moex_client: Client, check_day: domain.Day) -> None:
    table = await ctx.get_for_update(USD)

    start_day = table.last_row_date()
    rows = await moex_client.get_usd(start_day, check_day)

    table.update(rows)
