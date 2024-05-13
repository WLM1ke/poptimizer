import asyncio
from collections.abc import Iterator
from types import TracebackType
from typing import Self

from poptimizer.adapter import adapter, mongo
from poptimizer.domain.entity import entity
from poptimizer.domain.service import domain_service, view
from poptimizer.service import logging


class _IdentityMap:
    def __init__(self) -> None:
        self._seen: dict[tuple[type, entity.UID], tuple[entity.Entity, bool]] = {}
        self._lock = asyncio.Lock()

    def __iter__(self) -> Iterator[entity.Entity]:
        yield from (model for model, for_update in self._seen.values() if for_update)

    async def __aenter__(self) -> Self:
        await self._lock.acquire()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._lock.release()

    def get[E: entity.Entity](
        self,
        t_entity: type[E],
        uid: entity.UID,
        *,
        for_update: bool,
    ) -> E | None:
        entity, update_flag = self._seen.get((t_entity, uid), (None, False))
        if entity is None:
            return None

        if not isinstance(entity, t_entity):
            raise domain_service.ServiceError(f"type mismatch in identity map for {t_entity}({uid})")

        self._seen[entity.__class__, entity.uid] = (entity, update_flag or for_update)

        return entity

    def save(self, entity: entity.Entity, *, for_update: bool) -> None:
        saved, _ = self._seen.get((entity.__class__, entity.uid), (None, False))
        if saved is not None:
            raise domain_service.ServiceError(f"can't save to identity map {entity.__class__}({entity.uid})")

        self._seen[entity.__class__, entity.uid] = (entity, for_update)


class UOW:
    def __init__(
        self,
        logging_service: logging.Service,
        repo: mongo.Repo,
        viewer: view.Service,
    ) -> None:
        self._logging_service = logging_service
        self._repo = repo
        self._identity_map = _IdentityMap()
        self._viewer = viewer

    async def get[E: entity.Entity](
        self,
        t_entity: type[E],
        uid: entity.UID | None = None,
    ) -> E:
        uid = uid or entity.UID(adapter.get_component_name(t_entity))
        async with self._identity_map as identity_map:
            if loaded := identity_map.get(t_entity, uid, for_update=False):
                return loaded

            repo_entity = await self._repo.get(t_entity, uid)

            identity_map.save(repo_entity, for_update=False)

            return repo_entity

    async def get_for_update[E: entity.Entity](
        self,
        t_entity: type[E],
        uid: entity.UID | None = None,
    ) -> E:
        uid = uid or entity.UID(adapter.get_component_name(t_entity))
        async with self._identity_map as identity_map:
            if loaded := identity_map.get(t_entity, uid, for_update=True):
                return loaded

            repo_entity = await self._repo.get(t_entity, uid)

            identity_map.save(repo_entity, for_update=True)

            return repo_entity

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
        self._logging_service.info(msg)

    def warn(self, msg: str) -> None:
        self._logging_service.warn(msg)

    @property
    def viewer(self) -> view.Service:
        return self._viewer


class CtxFactory:
    def __init__(
        self,
        logging_service: logging.Service,
        repo: mongo.Repo,
        viewer: view.Service,
    ) -> None:
        self._logging_service = logging_service
        self._repo = repo
        self._viewer = viewer

    def __call__(self) -> UOW:
        return UOW(self._logging_service, self._repo, self._viewer)
