from typing import Annotated, NewType, Self

from pydantic import AfterValidator, BaseModel, Field, NonNegativeFloat, PositiveFloat, field_validator, model_validator

from poptimizer.domain import domain

Shareholder = NewType("Shareholder", str)


class Row(BaseModel):
    day: domain.Day
    value: PositiveFloat
    dividends: NonNegativeFloat
    inflows: dict[Shareholder, float]
    shares: dict[Shareholder, NonNegativeFloat]

    @model_validator(mode="after")
    def _check_shareholders(self) -> Self:
        if self.inflows.keys() - self.shares.keys():
            raise ValueError("shareholders and inflows mismatch")

        return self

    @field_validator("inflows")
    def _non_zero_inflows(cls, inflows: dict[Shareholder, float]) -> dict[Shareholder, float]:
        if any(inflow == 0 for inflow in inflows.values()):
            raise ValueError("inflows can't be zero")

        return inflows


class Fund(domain.Entity):
    rows: Annotated[
        list[Row],
        AfterValidator(domain.sorted_by_day_validator),
    ] = Field(default_factory=list[Row])

    def init(
        self,
        day: domain.Day,
        inflows: dict[Shareholder, float],
    ) -> None:
        if any(inflow < 0 for inflow in inflows.values()):
            raise ValueError("initial inflows can't be negative")

        all_inflows = sum(inflows.values())

        self.day = day
        self.rows = [
            Row(
                day=day,
                value=all_inflows,
                dividends=0,
                inflows=inflows,
                shares={shareholder: inflow / all_inflows for shareholder, inflow in inflows.items()},
            )
        ]

    def update(
        self,
        day: domain.Day,
        value: float,
        dividends: float,
        inflows: dict[Shareholder, float],
    ) -> None:
        if not self.rows:
            raise ValueError("fund is not initialized")

        last_row = self.rows[-1]

        if last_row.day >= day:
            raise ValueError("update day is not newer than last day")

        if last_row.day.month == day.month:
            raise ValueError("fund must be not updated in the same month")

        prev_value_share = 1 - sum(inflows.values()) / value
        all_shareholders = last_row.shares.keys() | inflows.keys()
        shares = {
            shareholder: last_row.shares.get(shareholder, 0) * prev_value_share + inflows.get(shareholder, 0) / value
            for shareholder in all_shareholders
        }

        self.day = day
        self.rows.append(
            Row(
                day=day,
                value=value,
                dividends=dividends,
                inflows=inflows,
                shares=shares,
            )
        )
