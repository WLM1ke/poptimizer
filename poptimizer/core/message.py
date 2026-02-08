from poptimizer.core import actors, consts


class AppStarted(actors.Message):
    version: str = consts.__version__


class Next(actors.Message): ...
