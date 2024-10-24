import asyncio
from collections.abc import Iterator
from types import TracebackType
from typing import Protocol, Self

from poptimizer import errors
from poptimizer.adapters import adapter, mongo
from poptimizer.domain import domain
from poptimizer.use_cases import handler


class _IdentityMap:
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
    ) -> None:
        self._lock.release()

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
            raise errors.ControllersError(f"type mismatch in identity map for {t_entity}({uid})")

        self._seen[entity.__class__, entity.uid] = (entity, update_flag or for_update)

        return entity

    def save(self, entity: domain.Entity, *, for_update: bool) -> None:
        saved, _ = self._seen.get((entity.__class__, entity.uid), (None, False))
        if saved is not None:
            raise errors.ControllersError(f"can't save to identity map {entity.__class__}({entity.uid})")

        self._seen[entity.__class__, entity.uid] = (entity, for_update)


class Bus(Protocol):
    def publish(self, msg: handler.Msg) -> None: ...


class UOW:
    def __init__(self, repo: mongo.Repo, bus: Bus) -> None:
        self._repo = repo
        self._identity_map = _IdentityMap()
        self._bus = bus
        self._messages: list[handler.Msg] = []

    async def get[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        uid = uid or domain.UID(adapter.get_component_name(t_entity))
        async with self._identity_map as identity_map:
            if loaded := identity_map.get(t_entity, uid, for_update=False):
                return loaded

            repo_entity = await self._repo.get(t_entity, uid)

            identity_map.save(repo_entity, for_update=False)

            return repo_entity

    async def get_for_update[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        uid = uid or domain.UID(adapter.get_component_name(t_entity))
        async with self._identity_map as identity_map:
            if loaded := identity_map.get(t_entity, uid, for_update=True):
                return loaded

            repo_entity = await self._repo.get(t_entity, uid)

            identity_map.save(repo_entity, for_update=True)

            return repo_entity

    def publish(self, msg: handler.Msg) -> None:
        self._messages.append(msg)

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

        async with asyncio.TaskGroup() as tg:
            for entity in self._identity_map:
                tg.create_task(self._repo.save(entity))

        for msg in self._messages:
            self._bus.publish(msg)


class Factory:
    def __init__(self, repo: mongo.Repo, bus: Bus) -> None:
        self._repo = repo
        self._bus = bus

    def __call__(self) -> UOW:
        return UOW(self._repo, self._bus)
