import asyncio
from collections.abc import Iterator
from types import TracebackType
from typing import Protocol, Self

from poptimizer import errors
from poptimizer.adapters import adapter, mongo
from poptimizer.domain import domain
from poptimizer.domain.evolve import evolve
from poptimizer.use_cases import handler


class _IdentityMap:
    def __init__(self) -> None:
        self._seen: dict[tuple[type, domain.UID], domain.Entity] = {}
        self._lock = asyncio.Lock()

    def __iter__(self) -> Iterator[domain.Entity]:
        yield from self._seen.values()

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

    def get[E: domain.Entity](self, t_entity: type[E], uid: domain.UID) -> E | None:
        entity = self._seen.get((t_entity, uid))
        if entity is None:
            return None

        if not isinstance(entity, t_entity):
            raise errors.ControllersError(f"type mismatch in identity map for {t_entity}({uid})")

        return entity

    def save(self, entity: domain.Entity) -> None:
        saved = self._seen.get((entity.__class__, entity.uid))
        if saved is not None:
            raise errors.ControllersError(f"{entity.__class__}({entity.uid}) in identity map ")

        self._seen[entity.__class__, entity.uid] = entity

    def delete(self, entity: domain.Entity) -> None:
        self._seen.pop((entity.__class__, entity.uid), None)


class Bus(Protocol):
    def publish(self, msg: handler.Msg) -> None: ...


class UOW:
    def __init__(self, repo: mongo.Repo) -> None:
        self._repo = repo
        self._identity_map = _IdentityMap()

    async def get[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        uid = uid or domain.UID(adapter.get_component_name(t_entity))
        async with self._identity_map as identity_map:
            return identity_map.get(t_entity, uid) or await self._repo.get(t_entity, uid)

    async def get_for_update[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        uid = uid or domain.UID(adapter.get_component_name(t_entity))
        async with self._identity_map as identity_map:
            if loaded := identity_map.get(t_entity, uid):
                return loaded

            entity = await self._repo.get(t_entity, uid)

            identity_map.save(entity)

            return entity

    async def delete(self, entity: domain.Entity) -> None:
        async with self._identity_map as identity_map:
            identity_map.delete(entity)
            await self._repo.delete(entity)

    async def count_models(self) -> int:
        return await self._repo.count_models()

    async def next_model_for_update(self) -> evolve.Model:
        async with self._identity_map as identity_map:
            entity = await self._repo.next_model()

            if loaded := identity_map.get(evolve.Model, entity.uid):
                return loaded

            identity_map.save(entity)

            return entity

    async def sample_models(self, n: int) -> list[evolve.Model]:
        return await self._repo.sample_models(n)

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
