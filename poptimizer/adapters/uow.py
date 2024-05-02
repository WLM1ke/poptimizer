import asyncio
from collections.abc import Iterator
from types import TracebackType
from typing import Literal, Self

from poptimizer.adapters import repo, telegram
from poptimizer.core import domain, errors


class IdentityMap:
    def __init__(self) -> None:
        self._seen: dict[tuple[type, domain.UID], tuple[domain.Entity, bool]] = {}
        self._lock = asyncio.Lock()

    def __iter__(self) -> Iterator[domain.Entity]:
        yield from (model for model, for_update in self._seen.values() if for_update)

    async def __aenter__(self) -> Self:
        await self._lock.acquire()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        self._lock.release()

        return False

    def get[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID,
        *,
        for_update: bool,
    ) -> E | None:
        entity, update_flag = self._seen.get((t_entity, uid), (None, False))
        if entity is None:
            return None

        if not isinstance(entity, t_entity):
            raise errors.AdaptersError(f"type mismatch in identity map for {t_entity}({uid})")

        self._seen[entity.__class__, entity.uid] = (entity, update_flag or for_update)

        return entity

    def save(self, entity: domain.Entity, *, for_update: bool) -> None:
        saved, _ = self._seen.get((entity.__class__, entity.uid), (None, False))
        if saved is not None:
            raise errors.AdaptersError(f"can't save to identity map {entity.__class__}({entity.uid})")

        self._seen[entity.__class__, entity.uid] = (entity, for_update)


class UOW:
    def __init__(
        self,
        logger: telegram.Logger,
        repo: repo.Mongo,
        identity_map: IdentityMap,
        viewer: domain.Viewer,
    ) -> None:
        self._logger = logger
        self._repo = repo
        self._identity_map = identity_map
        self._viewer = viewer

    async def get[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
        *,
        for_update: bool = True,
    ) -> E:
        uid = uid or domain.UID(domain.get_component_name(t_entity))
        async with self._identity_map as identity_map:
            if loaded := identity_map.get(t_entity, uid, for_update=for_update):
                return loaded

            entity = await self._repo.get(t_entity, uid)

            identity_map.save(entity, for_update=for_update)

            return entity

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_value is not None:
            return

        await self._repo.save(self._identity_map)

    def info(self, msg: str) -> None:
        self._logger.info(msg)

    def warn(self, msg: str) -> None:
        self._logger.warning(msg)

    @property
    def viewer(self) -> domain.Viewer:
        return self._viewer


class CtxFactory:
    def __init__(
        self,
        logger: telegram.Logger,
        repo: repo.Mongo,
        viewer: domain.Viewer,
    ) -> None:
        self._logger = logger
        self._repo = repo
        self._viewer = viewer

    def __call__(self) -> UOW:
        return UOW(self._logger, self._repo, IdentityMap(), self._viewer)
