import asyncio
from collections.abc import Iterator
from types import TracebackType
from typing import Protocol, Self

from poptimizer.core import actors, domain, errors
from poptimizer.domain.evolve import evolve


class _IdentityMap:
    def __init__(self) -> None:
        self._seen: dict[tuple[type, domain.UID], tuple[domain.Entity, bool]] = {}
        self._lock = asyncio.Lock()

    def __iter__(self) -> Iterator[domain.Entity]:
        yield from (entity for entity, dirty in self._seen.values() if dirty)

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
        saved = self._seen.get((t_entity, uid))
        if saved is None:
            return None

        entity, _ = saved

        if not isinstance(entity, t_entity):
            raise errors.ControllersError(f"type mismatch in identity map for {t_entity}({uid})")

        return entity

    def get_for_update[E: domain.Entity](self, t_entity: type[E], uid: domain.UID) -> E | None:
        saved = self._seen.get((t_entity, uid))
        if saved is None:
            return None

        entity, dirty = saved
        if not dirty:
            self._seen[entity.__class__, entity.uid] = (entity, True)

        if not isinstance(entity, t_entity):
            raise errors.ControllersError(f"type mismatch in identity map for {t_entity}({uid})")

        return entity

    def save(self, entity: domain.Entity) -> None:
        saved = self._seen.get((entity.__class__, entity.uid))
        if saved is not None:
            raise errors.ControllersError(f"{entity.__class__}({entity.uid}) in identity map")

        self._seen[entity.__class__, entity.uid] = (entity, False)

    def save_for_update(self, entity: domain.Entity) -> None:
        saved = self._seen.get((entity.__class__, entity.uid))
        if saved is not None:
            raise errors.ControllersError(f"{entity.__class__}({entity.uid}) in identity map")

        self._seen[entity.__class__, entity.uid] = (entity, True)

    def delete(self, entity: domain.Entity) -> None:
        self._seen.pop((entity.__class__, entity.uid), None)

    def clear(self) -> None:
        self._seen.clear()


class Repo(Protocol):
    async def get[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E: ...
    async def delete(self, entity: domain.Entity) -> None: ...
    async def count_models(self) -> int: ...
    async def next_model(self, uid: domain.UID) -> tuple[evolve.Model, bool]: ...
    async def sample_models(self, n: int) -> list[evolve.Model]: ...
    async def save(self, entity: domain.Entity) -> None: ...


class UOW:
    def __init__(self, repo: Repo) -> None:
        self._repo = repo
        self._identity_map = _IdentityMap()

    async def get[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        uid = uid or domain.UID(actors.get_component_name(t_entity))

        async with self._identity_map as identity_map:
            if loaded := identity_map.get(t_entity, uid):
                return loaded

            entity = await self._repo.get(t_entity, uid)
            identity_map.save(entity)

            return entity

    async def get_for_update[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        uid = uid or domain.UID(actors.get_component_name(t_entity))

        async with self._identity_map as identity_map:
            if loaded := identity_map.get_for_update(t_entity, uid):
                return loaded

            entity = await self._repo.get(t_entity, uid)
            identity_map.save_for_update(entity)

            return entity

    async def delete(self, entity: domain.Entity) -> None:
        async with self._identity_map as identity_map:
            await self._repo.delete(entity)
            identity_map.delete(entity)

    async def count_models(self) -> int:
        return await self._repo.count_models()

    async def next_model_for_update(self, uid: domain.UID) -> tuple[evolve.Model, bool]:
        entity, good = await self._repo.next_model(uid)

        async with self._identity_map as identity_map:
            if not identity_map.get_for_update(evolve.Model, entity.uid):
                identity_map.save_for_update(entity)

            return entity, good

    async def sample_models(self, n: int) -> list[evolve.Model]:
        models = await self._repo.sample_models(n)

        for model in models:
            async with self._identity_map as identity_map:
                if not identity_map.get(evolve.Model, model.uid):
                    identity_map.save(model)

        return models

    async def save(self) -> None:
        async with asyncio.TaskGroup() as tg:
            for entity in self._identity_map:
                tg.create_task(self._repo.save(entity))

    def clear(self) -> None:
        self._identity_map.clear()
