from poptimizer.core import actors


class AppStarted(actors.Message):
    version: str
    next_aid: actors.AID


class MigrationFinished(actors.Message): ...
