from pydantic import Field

from poptimizer.core import domain, fsm


class AppStopped(fsm.Event): ...


class AppStarted(fsm.Event): ...


class VersionChanged(fsm.Event): ...


class VersionNotChanged(fsm.Event): ...


class UpdateRequired(fsm.Event): ...


class DataUpdated(fsm.Event):
    trading_days: list[domain.Day] = Field(repr=False)


class FeaturesUpdated(fsm.Event): ...
