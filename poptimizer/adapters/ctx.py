from poptimizer.adapters import repo, telegram, uow


class Factory:
    def __init__(
        self,
        logger: telegram.Logger,
        repo: repo.Mongo,
    ) -> None:
        self._logger = logger
        self._repo = repo

    def __call__(self) -> uow.UOW:
        return uow.UOW(self._logger, self._repo, uow.IdentityMap())
