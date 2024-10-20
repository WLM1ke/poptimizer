from pydantic import PositiveInt

from poptimizer.domain.entity import entity


class Evolution(entity.Entity):
    tests: PositiveInt = 1
    step: PositiveInt = 1
    prev_org_uid: str = ""
