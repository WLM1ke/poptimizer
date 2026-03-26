import asyncio
from collections.abc import AsyncIterator, Iterator
from types import TracebackType
from typing import NewType, Protocol, Self

from poptimizer.core import domain, errors
from poptimizer.evolve.evolution import evolve

Version = NewType("Version", int)


class _IdentityMap:
    def __init__(self) -> None:
        self._seen: dict[tuple[type, domain.UID], tuple[domain.Object, Version, bool]] = {}
        self._lock = asyncio.Lock()

    def __iter__(self) -> Iterator[tuple[domain.Object, Version]]:
        yield from ((obj, ver) for obj, ver, dirty in self._seen.values() if dirty)

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

    def get[E: domain.Object](self, t_obj: type[E], uid: domain.UID) -> tuple[E, Version] | None:
        saved = self._seen.get((t_obj, uid))
        if saved is None:
            return None

        obj, ver, _ = saved

        if not isinstance(obj, t_obj):
            raise errors.ControllersError(f"type mismatch in identity map for {t_obj}({uid})")

        return obj, ver

    def get_for_update[E: domain.Object](self, t_obj: type[E], uid: domain.UID) -> tuple[E, Version] | None:
        saved = self._seen.get((t_obj, uid))
        if saved is None:
            return None

        obj, ver, dirty = saved
        if not dirty:
            self._seen[obj.__class__, obj.uid] = (obj, ver, True)

        if not isinstance(obj, t_obj):
            raise errors.ControllersError(f"type mismatch in identity map for {t_obj}({uid})")

        return obj, ver

    def save(self, obj: domain.Object, ver: Version) -> None:
        saved = self._seen.get((obj.__class__, obj.uid))
        if saved is not None:
            raise errors.ControllersError(f"{obj.__class__}({obj.uid}) in identity map")

        self._seen[obj.__class__, obj.uid] = (obj, ver, False)

    def save_for_update(self, obj: domain.Object, ver: Version) -> None:
        saved = self._seen.get((obj.__class__, obj.uid))
        if saved is not None:
            raise errors.ControllersError(f"{obj.__class__}({obj.uid}) in identity map")

        self._seen[obj.__class__, obj.uid] = (obj, ver, True)

    def delete(self, obj: domain.Object) -> None:
        self._seen.pop((obj.__class__, obj.uid), None)

    def clear(self) -> None:
        self._seen.clear()


class Repo(Protocol):
    async def get[E: domain.Object](
        self,
        t_obj: type[E],
        uid: domain.UID,
    ) -> tuple[E, Version]: ...
    async def save(self, obj: domain.Object, ver: Version) -> None: ...
    async def delete(self, obj: domain.Object) -> None: ...
    async def count_models(self) -> int: ...
    async def next_model_for_update(self) -> tuple[evolve.Model, Version]: ...
    async def get_models(self, day: domain.Day) -> list[evolve.Model]: ...
    async def sample_models(self, n: int) -> list[evolve.Model]: ...
    def get_all[E: domain.Object](self, t_obj: type[E]) -> AsyncIterator[E]: ...
    async def drop(self, obj_type: type[domain.Object]) -> None: ...


class UOW:
    def __init__(self, repo: Repo) -> None:
        self._repo = repo
        self._identity_map = _IdentityMap()

    async def get[E: domain.Object](
        self,
        t_obj: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        uid = uid or domain.UID(t_obj.__name__)

        async with self._identity_map as identity_map:
            if loaded := identity_map.get(t_obj, uid):
                obj, _ = loaded

                return obj

            obj, ver = await self._repo.get(t_obj, uid)
            identity_map.save(obj, ver)

            return obj

    async def get_for_update[E: domain.Object](
        self,
        t_obj: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        uid = uid or domain.UID(t_obj.__name__)

        async with self._identity_map as identity_map:
            if loaded := identity_map.get_for_update(t_obj, uid):
                obj, _ = loaded

                return obj

            obj, ver = await self._repo.get(t_obj, uid)
            identity_map.save_for_update(obj, ver)

            return obj

    async def delete(self, obj: domain.Object) -> None:
        async with self._identity_map as identity_map:
            await self._repo.delete(obj)
            identity_map.delete(obj)

    async def count_models(self) -> int:
        return await self._repo.count_models()

    async def next_model_for_update(self) -> evolve.Model:
        async with self._identity_map as identity_map:
            model, ver = await self._repo.next_model_for_update()
            if loaded := identity_map.get_for_update(evolve.Model, model.uid):
                obj, _ = loaded

                return obj

            identity_map.save_for_update(model, ver)

            return model

    async def get_models(self, day: domain.Day) -> list[evolve.Model]:
        return await self._repo.get_models(day)

    async def sample_models(self, n: int) -> list[evolve.Model]:
        return await self._repo.sample_models(n)

    def get_all[E: domain.Object](
        self,
        t_obj: type[E],
    ) -> AsyncIterator[E]:
        return self._repo.get_all(t_obj)

    async def drop(self, obj_type: type[domain.Object]) -> None:
        await self._repo.drop(obj_type)

    async def save(self) -> None:
        async with asyncio.TaskGroup() as tg:
            for obj, ver in self._identity_map:
                tg.create_task(self._repo.save(obj, ver))

    def clear(self) -> None:
        self._identity_map.clear()
