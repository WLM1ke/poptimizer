from datetime import datetime

from pydantic import Field

from poptimizer.core import domain, fsm


class PortfolioUpdated(fsm.Event): ...


class PortfolioRevalued(fsm.Event):
    trading_days: list[domain.Day] = Field(repr=False)


class PositionChecked(fsm.Event):
    updated_at: datetime
