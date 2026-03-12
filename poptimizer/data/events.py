from pydantic import Field

from poptimizer.core import domain, fsm


class VersionChanged(fsm.Event): ...


class QuotesUpdateRequired(fsm.Event): ...


class QuotesUpdated(fsm.Event):
    trading_days: list[domain.Day] = Field(repr=False)


class DataUpdated(fsm.Event):
    day: domain.Day


class DayNotChanged(fsm.Event): ...
