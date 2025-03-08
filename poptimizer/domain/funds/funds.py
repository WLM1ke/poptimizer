from typing import Annotated, NewType, Self

from pydantic import AfterValidator, BaseModel, Field, NonNegativeFloat, PositiveFloat, field_validator, model_validator

from poptimizer.domain import domain

Investor = NewType("Investor", str)


class Row(BaseModel):
    day: domain.Day
    value: PositiveFloat
    dividends: NonNegativeFloat
    inflows: dict[Investor, float]
    shares: dict[Investor, NonNegativeFloat]

    @model_validator(mode="after")
    def _check_investors(self) -> Self:
        if self.inflows.keys() - self.shares.keys():
            raise ValueError("investors and inflows mismatch")

        return self

    @field_validator("inflows")
    def _non_zero_inflows(cls, inflows: dict[Investor, float]) -> dict[Investor, float]:
        if any(inflow == 0 for inflow in inflows.values()):
            raise ValueError("inflows can't be zero")

        return inflows

    def get_value(self, investor: Investor) -> float:
        return self.shares.get(investor, 0) * self.value

    def get_pre_inflow_value(self, investor: Investor) -> float:
        return self.shares.get(investor, 0) * self.value - self.inflows.get(investor, 0)

    def get_inflow(self, investor: Investor) -> float:
        return self.inflows.get(investor, 0)

    def get_share(self, investor: Investor) -> float:
        return self.shares.get(investor, 0)

    def get_pre_inflow_share(self, investor: Investor) -> float:
        return (self.shares.get(investor, 0) * self.value - self.get_inflow(investor)) / self.pre_inflow_value

    def get_dividends(self, investor: Investor) -> float:
        return self.shares.get(investor, 0) * self.dividends

    @property
    def pre_inflow_value(self) -> float:
        return self.value - sum(self.inflows.values())

    @property
    def inflow(self) -> float:
        return sum(self.inflows.values())


class Fund(domain.Entity):
    rows: Annotated[
        list[Row],
        AfterValidator(domain.sorted_by_day_validator),
    ] = Field(default_factory=list[Row])

    def init(
        self,
        day: domain.Day,
        inflows: dict[Investor, float],
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
                shares={investor: inflow / all_inflows for investor, inflow in inflows.items()},
            )
        ]

    def update(
        self,
        day: domain.Day,
        value: float,
        dividends: float,
        inflows: dict[Investor, float],
    ) -> None:
        if not self.rows:
            raise ValueError("fund is not initialized")

        last_row = self.rows[-1]

        if last_row.day >= day:
            raise ValueError("update day is not newer than last day")

        if last_row.day.month == day.month:
            raise ValueError("fund must be not updated in the same month")

        prev_value_share = 1 - sum(inflows.values()) / value
        all_investors = last_row.shares.keys() | inflows.keys()
        shares = {
            investors: last_row.shares.get(investors, 0) * prev_value_share + inflows.get(investors, 0) / value
            for investors in all_investors
        }
        all_shares = sum(shares.values())
        shares = {investor: share / all_shares for investor, share in shares.items()}

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
