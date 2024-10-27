from pydantic import PositiveInt

from poptimizer.domain import domain


class Evolution(domain.Entity):
    tests: PositiveInt = 1
    step: PositiveInt = 1
    prev_org_uid: str = ""
