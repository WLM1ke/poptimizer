from pydantic import Field, NonNegativeInt, PositiveInt

from poptimizer.domain import domain


class Evolution(domain.Entity):
    step: PositiveInt = 1
    tickers: tuple[domain.Ticker, ...] = Field(default_factory=tuple)
    next_days: list[domain.Day] = Field(default_factory=list)
    tests_initial: NonNegativeInt = 0
    tests_step: PositiveInt = 1
    prev_org_uid: str = ""
