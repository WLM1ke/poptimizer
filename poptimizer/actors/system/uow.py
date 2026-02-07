import asyncio
from collections.abc import AsyncIterator, Iterator
from types import TracebackType
from typing import Protocol, Self

from poptimizer.core import domain, errors
from poptimizer.domain.evolve import evolve


class _IdentityMap:
    def __init__(self) -> None:
        self._seen: dict[tuple[type, domain.UID], tuple[domain.Versioned, bool]] = {}
        self._lock = asyncio.Lock()

    def __iter__(self) -> Iterator[domain.Versioned]:
        yield from (versioned for versioned, dirty in self._seen.values() if dirty)

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

    def get[E: domain.Versioned](self, t_versioned: type[E], uid: domain.UID) -> E | None:
        saved = self._seen.get((t_versioned, uid))
        if saved is None:
            return None

        versioned, _ = saved

        if not isinstance(versioned, t_versioned):
            raise errors.ControllersError(f"type mismatch in identity map for {t_versioned}({uid})")

        return versioned

    def get_for_update[E: domain.Versioned](self, t_versioned: type[E], uid: domain.UID) -> E | None:
        saved = self._seen.get((t_versioned, uid))
        if saved is None:
            return None

        versioned, dirty = saved
        if not dirty:
            self._seen[versioned.__class__, versioned.uid] = (versioned, True)

        if not isinstance(versioned, t_versioned):
            raise errors.ControllersError(f"type mismatch in identity map for {t_versioned}({uid})")

        return versioned

    def save(self, versioned: domain.Versioned) -> None:
        saved = self._seen.get((versioned.__class__, versioned.uid))
        if saved is not None:
            raise errors.ControllersError(f"{versioned.__class__}({versioned.uid}) in identity map")

        self._seen[versioned.__class__, versioned.uid] = (versioned, False)

    def save_for_update(self, versioned: domain.Versioned) -> None:
        saved = self._seen.get((versioned.__class__, versioned.uid))
        if saved is not None:
            raise errors.ControllersError(f"{versioned.__class__}({versioned.uid}) in identity map")

        self._seen[versioned.__class__, versioned.uid] = (versioned, True)

    def delete(self, versioned: domain.Versioned) -> None:
        self._seen.pop((versioned.__class__, versioned.uid), None)

    def clear(self) -> None:
        self._seen.clear()


class Repo(Protocol):
    async def get[E: domain.Versioned](
        self,
        t_versioned: type[E],
        uid: domain.UID | None = None,
    ) -> E: ...
    async def delete(self, versioned: domain.Versioned) -> None: ...
    async def count_models(self) -> int: ...
    async def next_model(self, uid: domain.UID) -> tuple[evolve.Model, bool]: ...
    async def sample_models(self, n: int) -> list[evolve.Model]: ...
    async def save(self, versioned: domain.Versioned) -> None: ...
    def get_all[E: domain.Versioned](self, t_versioned: type[E]) -> AsyncIterator[E]: ...
    async def drop(self, versioned_type: type[domain.Versioned]) -> None: ...


class UOW:
    def __init__(self, repo: Repo) -> None:
        self._repo = repo
        self._identity_map = _IdentityMap()

    async def get[E: domain.Versioned](
        self,
        t_versioned: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        uid = uid or domain.UID(t_versioned.__name__)

        async with self._identity_map as identity_map:
            if loaded := identity_map.get(t_versioned, uid):
                return loaded

            versioned = await self._repo.get(t_versioned, uid)
            identity_map.save(versioned)

            return versioned

    async def get_for_update[E: domain.Versioned](
        self,
        t_versioned: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        uid = uid or domain.UID(t_versioned.__name__)

        async with self._identity_map as identity_map:
            if loaded := identity_map.get_for_update(t_versioned, uid):
                return loaded

            versioned = await self._repo.get(t_versioned, uid)
            identity_map.save_for_update(versioned)

            return versioned

    async def delete(self, versioned: domain.Versioned) -> None:
        async with self._identity_map as identity_map:
            await self._repo.delete(versioned)
            identity_map.delete(versioned)

    async def count_models(self) -> int:
        return await self._repo.count_models()

    async def next_model_for_update(self, uid: domain.UID) -> tuple[evolve.Model, bool]:
        versioned, good = await self._repo.next_model(uid)

        async with self._identity_map as identity_map:
            if not identity_map.get_for_update(evolve.Model, versioned.uid):
                identity_map.save_for_update(versioned)

            return versioned, good

    async def sample_models(self, n: int) -> list[evolve.Model]:
        models = await self._repo.sample_models(n)

        for model in models:
            async with self._identity_map as identity_map:
                if not identity_map.get(evolve.Model, model.uid):
                    identity_map.save(model)

        return models

    def get_all[E: domain.Versioned](
        self,
        t_versioned: type[E],
    ) -> AsyncIterator[E]:
        return self._repo.get_all(t_versioned)

    async def drop(self, versioned_type: type[domain.Versioned]) -> None:
        await self._repo.drop(versioned_type)

    async def save(self) -> None:
        async with asyncio.TaskGroup() as tg:
            for versioned in self._identity_map:
                tg.create_task(self._repo.save(versioned))

    def clear(self) -> None:
        self._identity_map.clear()
