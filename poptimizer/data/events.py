from poptimizer.core import fsm


class AppStarted(fsm.Event): ...


class AppVersionChanged(fsm.Event): ...


class AppVersionNotChanged(fsm.Event): ...
