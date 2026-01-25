import asyncio
import logging
import random
import traceback as tb
from collections.abc import Iterable, Iterator
from datetime import timedelta
from types import TracebackType
from typing import Final, Protocol, Self

from poptimizer import errors
from poptimizer.actors import actor
from poptimizer.adapters import adapter
from poptimizer.domain import domain
from poptimizer.domain.evolve import evolve

_FIRST_RETRY: Final = timedelta(seconds=30)
_BACKOFF_FACTOR: Final = 2


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


class _Repo(Protocol):
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
    def __init__(self, repo: _Repo) -> None:
        self._lgr = logging.getLogger(__name__)
        self._repo = repo
        self._identity_map = _IdentityMap()
        self._outbox_current: list[tuple[actor.PID, actor.Message]] = []
        self._outbox: list[tuple[actor.PID, actor.Message]] = []
        self._running = False

    async def run_with_retry[**I, O](self, handler: actor.Handler[I, O], *args: I.args, **kwargs: I.kwargs) -> O:
        match self._running:
            case True:
                uow = UOW(self._repo)
                output = await uow.run_with_retry(handler, *args, **kwargs)
                self._outbox.extend(uow.outbox())

                return output
            case False:
                self._running = True
                return await self._run_with_retry(handler, *args, **kwargs)

    async def _run_with_retry[**I, O](
        self,
        handler: actor.Handler[I, O],
        *args: I.args,
        **kwargs: I.kwargs,
    ) -> O:
        last_delay = _FIRST_RETRY / _BACKOFF_FACTOR

        while True:
            match await self._run_safe(handler, *args, **kwargs):
                case errors.POError() as err:
                    self._identity_map = _IdentityMap()
                    self._outbox_current.clear()

                    last_delay = await _next_delay(last_delay)
                    self._lgr.warning(
                        "%s failed: %s - retrying in %s",
                        adapter.get_component_name(handler),
                        err,
                        last_delay,
                    )

                    await asyncio.sleep(last_delay.total_seconds())
                case _ as output:
                    self._lgr.info(
                        "%s handled",
                        adapter.get_component_name(handler),
                    )

                    return output

    async def _run_safe[**I, O](
        self,
        handler: actor.Handler[I, O],
        *args: I.args,
        **kwargs: I.kwargs,
    ) -> O | errors.POError:
        err_out: errors.POError = errors.POError()

        try:
            return await self._run(handler, *args, **kwargs)
        except* errors.POError as err:
            tb.print_exception(err, colorize=True)  # type: ignore[reportCallIssue]

            err_out = errors.get_root_poptimizer_error(err)

        return err_out

    async def _run[**I, O](
        self,
        handler: actor.Handler[I, O],
        *args: I.args,
        **kwargs: I.kwargs,
    ) -> O:
        output = await handler(self, *args, **kwargs)

        async with asyncio.TaskGroup() as tg:
            for entity in self._identity_map:
                tg.create_task(self._repo.save(entity))

        self._outbox.extend(self._outbox_current)

        return output

    def send(self, pid: actor.PID, msg: actor.Message) -> None:
        self._outbox_current.append((pid, msg))

    def outbox(self) -> Iterable[tuple[actor.PID, actor.Message]]:
        outbox = self._outbox
        self._outboxes = []

        yield from outbox

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

    async def next_model_for_update(self, uid: domain.UID) -> tuple[evolve.Model, bool]:
        async with self._identity_map as identity_map:
            entity, good = await self._repo.next_model(uid)

            if not identity_map.get(evolve.Model, entity.uid):
                identity_map.save(entity)

            return entity, good

    async def sample_models(self, n: int) -> list[evolve.Model]:
        return await self._repo.sample_models(n)


async def _next_delay(delay: timedelta) -> timedelta:
    return timedelta(seconds=delay.total_seconds() * _BACKOFF_FACTOR * 2 * random.random())  # noqa: S311
