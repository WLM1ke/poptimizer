from __future__ import annotations

from typing import Final

from pydantic import PositiveInt

from poptimizer.core import consts, domain
from poptimizer.domain.dl import datasets

_INITIAL_MINIMAL_RETURNS_DAYS: Final = datasets.Days(
    history=consts.INITIAL_HISTORY_DAYS_END,
    forecast=consts.INITIAL_FORECAST_DAYS,
    test=consts.INITIAL_TEST_DAYS,
).minimal_returns_days


class Evolution(domain.Entity):
    minimal_returns_days: PositiveInt = _INITIAL_MINIMAL_RETURNS_DAYS
