import asyncio
import functools
import logging
import traceback
from collections import defaultdict
from collections.abc import Awaitable, Iterable
from datetime import timedelta
from typing import (
    Any,
    Final,
    Protocol,
    get_args,
    get_type_hints,
)

from poptimizer import errors
from poptimizer.adapters import adapter, logger, mongo
from poptimizer.controllers.bus import uow
from poptimizer.domain import domain
from poptimizer.domain.evolve import evolve
from poptimizer.use_cases.handler import AppStarted, Event

_DEFAULT_FIRST_RETRY: Final = timedelta(seconds=30)
_DEFAULT_BACKOFF_FACTOR: Final = 2


class Ctx(Protocol):
    def publish(self, msg: Event) -> None: ...

    async def get[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E: ...

    async def get_for_update[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E: ...

    async def delete(self, entity: domain.Entity) -> None: ...

    async def count_models(self) -> int: ...

    async def next_model_for_update(self, uid: domain.UID) -> tuple[evolve.Model, bool]: ...

    async def sample_models(self, n: int) -> list[evolve.Model]: ...


class EventHandler[E: Event](Protocol):
    async def __call__(self, ctx: Ctx, msg: E) -> None: ...


def _handler_types(handler: EventHandler[Any]) -> Iterable[adapter.Component]:
    if not (msg_type := get_type_hints(handler.__call__).get("msg")):
        msg_type = get_type_hints(handler)["msg"]

    msg_type_union = get_args(msg_type)
    if not msg_type_union:
        msg_type_union = (msg_type,)

    return (adapter.get_component_name(msg_subtype) for msg_subtype in msg_type_union)


class Policy(Protocol):
    def __init__(self) -> None: ...

    async def try_again(self) -> bool: ...


class IgnoreErrorsPolicy:
    async def try_again(self) -> bool:
        return False


class IndefiniteRetryPolicy:
    def __init__(
        self,
        first_retry: timedelta = _DEFAULT_FIRST_RETRY,
        backoff_factor: float = _DEFAULT_BACKOFF_FACTOR,
    ) -> None:
        self._first_retry = first_retry.total_seconds()
        self._backoff_factor = backoff_factor
        self._attempt = 0

    async def try_again(self) -> bool:
        self._attempt += 1
        await asyncio.sleep(self._first_retry * self._backoff_factor ** (self._attempt - 1))

        return True


class Handler[**Req, Resp](Protocol):
    def __call__(self, ctx: Ctx, *args: Req.args, **kwargs: Req.kwargs) -> Awaitable[Resp]: ...


class WrappedHandler[**Req, Resp](Protocol):
    def __call__(self, *args: Req.args, **kwargs: Req.kwargs) -> Awaitable[Resp]: ...


class Bus:
    def __init__(
        self,
        repo: mongo.Repo,
    ) -> None:
        self._lgr = logging.getLogger()
        self._repo = repo
        self._tg = asyncio.TaskGroup()
        self._event_handlers: dict[adapter.Component, list[tuple[EventHandler[Any], type[Policy]]]] = defaultdict(list)

    def register_event_handler(
        self,
        handler: EventHandler[Any],
        policy_type: type[Policy],
    ) -> None:
        for msg_name in _handler_types(handler):
            self._event_handlers[msg_name].append((handler, policy_type))
            self._lgr.info(
                "%s was registered as event handler for %s with %s",
                adapter.get_component_name(handler),
                msg_name,
                adapter.get_component_name(policy_type),
            )

    async def run(self) -> None:
        self._lgr.info("Message bus started")
        try:
            async with self._tg:
                self.publish(AppStarted())
        except asyncio.CancelledError:
            self._lgr.info("Message bus shutdown finished")

    def publish(self, msg: Event) -> None:
        self._tg.create_task(self._route_event(msg))

    async def _route_event(self, msg: Event) -> None:
        name = adapter.get_component_name(msg)
        self._lgr.info("%r published", msg)

        handlers = self._event_handlers.get(name)
        if not handlers:
            raise errors.ControllersError(f"No event handler for {name}")

        for handler, policy_type in handlers:
            self._tg.create_task(self._handle_event(handler, msg, policy_type()))

    async def _handle_event(
        self,
        handler: EventHandler[Any],
        msg: Event,
        policy: Policy,
    ) -> None:
        attempt = 1

        while await self._handle_event_safe(handler, msg, attempt):
            attempt += 1

            if not await policy.try_again():
                return

        self._lgr.info(
            "%s handled %r",
            adapter.get_component_name(handler),
            msg,
        )

    async def _handle_event_safe(
        self,
        handler: EventHandler[Any],
        msg: Event,
        attempt: int,
    ) -> bool:
        try:
            async with uow.UOW(self._repo) as ctx:
                await handler(ctx, msg)

                for event in ctx.events():
                    self.publish(event)

        except* errors.POError as err:
            self._lgr.warning(
                "%s can't handle %r in %d attempt: %s",
                adapter.get_component_name(handler),
                msg,
                attempt,
                logger.get_root_error(err),
            )
            traceback.print_exception(err, colorize=True)  # type: ignore[reportCallIssue]
        else:
            return False

        return True

    def wrap[**Req, Resp](
        self,
        handler: Handler[Req, Resp],
    ) -> WrappedHandler[Req, Resp]:
        @functools.wraps(handler)
        async def wrapped(*args: Req.args, **kwargs: Req.kwargs) -> Resp:
            async with uow.UOW(self._repo) as ctx:
                resp = await handler(ctx, *args, **kwargs)

                for event in ctx.events():
                    self.publish(event)

                return resp

        return wrapped
