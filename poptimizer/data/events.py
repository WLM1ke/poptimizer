from pydantic import Field

from poptimizer.core import domain, fsm


class AppStopped(fsm.Event): ...


class AppStarted(fsm.Event): ...


class VersionChanged(fsm.Event): ...


class QuotesUpdateRequired(fsm.Event): ...


class QuotesUpdated(fsm.Event):
    trading_days: list[domain.Day] = Field(repr=False)


class DataUpdated(fsm.Event): ...
