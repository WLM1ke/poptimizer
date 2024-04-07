from poptimizer.adapters import lgr, repo, uow


class Factory:
    def __init__(
        self,
        logger: lgr.TelegramLogger,
        repo: repo.Mongo,
        identity_map: uow.IdentityMap,
    ) -> None:
        self._logger = logger
        self._repo = repo
        self._identity_map = identity_map

    def __call__(self) -> uow.UOW:
        return uow.UOW(self._logger, self._repo, self._identity_map)
