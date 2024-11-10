from pydantic import NonNegativeInt, PositiveInt

from poptimizer.domain import domain


class Evolution(domain.Entity):
    step: PositiveInt = 1
    tickers: tuple[domain.Ticker, ...] = ()
    tests_initial: NonNegativeInt = 0
    tests_step: PositiveInt = 1
    prev_org_uid: str = ""
