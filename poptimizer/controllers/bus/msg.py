import asyncio
import logging
from collections import defaultdict
from collections.abc import AsyncIterator, Iterable
from datetime import timedelta
from typing import (
    Any,
    Final,
    Protocol,
    get_args,
    get_type_hints,
)

from poptimizer import errors
from poptimizer.adapters import adapter, mongo
from poptimizer.controllers.bus import uow
from poptimizer.domain import domain
from poptimizer.domain.evolve import model
from poptimizer.use_cases.handler import DTO, AppStarted, Event

_DEFAULT_FIRST_RETRY: Final = timedelta(seconds=30)
_DEFAULT_BACKOFF_FACTOR: Final = 2


class Ctx(Protocol):
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

    async def count_orgs(self) -> int: ...

    async def iter_orgs(self) -> AsyncIterator[model.Model]: ...

    async def next_org_for_update(self) -> model.Model: ...

    async def sample_orgs(self, n: int) -> list[model.Model]: ...


class RequestHandler[D: DTO, E: Event](Protocol):
    async def __call__(self, ctx: Ctx, msg: D) -> tuple[D, E] | D: ...


class EventHandler[E: Event](Protocol):
    async def __call__(self, ctx: Ctx, msg: E) -> Iterable[E] | E | None: ...


type Handler = RequestHandler[Any, Any] | EventHandler[Any]


def _handler_types(handler: Handler) -> Iterable[adapter.Component]:
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


class Bus:
    def __init__(
        self,
        repo: mongo.Repo,
    ) -> None:
        self._lgr = logging.getLogger()
        self._repo = repo
        self._tg = asyncio.TaskGroup()
        self._event_handlers: dict[adapter.Component, list[tuple[EventHandler[Any], type[Policy]]]] = defaultdict(list)
        self._request_handlers: dict[adapter.Component, RequestHandler[Any, Any]] = {}

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

    def register_request_handler(
        self,
        handler: RequestHandler[Any, Any],
    ) -> None:
        for msg_name in _handler_types(handler):
            if msg_name in self._request_handlers:
                raise errors.ControllersError(f"not unique request handler for {msg_name}")

            self._request_handlers[msg_name] = handler
            self._lgr.info(
                "%s was registered as request handler for %s",
                adapter.get_component_name(handler),
                msg_name,
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
        attempt = 0

        while err := await self._handle_event_safe(handler, msg):
            attempt += 1
            self._lgr.warning(
                "%s can't handle %r in %d attempt with %s, ...",
                adapter.get_component_name(handler),
                msg,
                attempt,
                err.exceptions[0],
            )

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
    ) -> BaseExceptionGroup[errors.POError] | None:
        error: BaseExceptionGroup[errors.POError] | None = None
        try:
            async with uow.UOW(self._repo) as ctx:
                result = await handler(ctx, msg)
        except* errors.POError as err:
            error = err
        else:
            match result:
                case None:
                    events = []
                case Event():
                    events = [result]
                case _:
                    events = result

            for event in events:
                self.publish(event)

        return error

    async def request(self, msg: DTO) -> DTO:
        name = adapter.get_component_name(msg)
        self._lgr.info("%r published", msg)

        handler = self._request_handlers.get(name)
        if handler is None:
            raise errors.ControllersError(f"No request handler for {name}")

        return await self._handle_request(handler, msg)

    async def _handle_request(
        self,
        handler: RequestHandler[Any, Any],
        msg: DTO,
    ) -> DTO:
        async with uow.UOW(self._repo) as ctx:
            result = await handler(ctx, msg)

        match result:
            case DTO():
                return result
            case (DTO() as dto, Event() as event):
                self.publish(event)

                return dto
            case _:
                raise errors.ControllersError(f"Invalid request handler result {adapter.get_component_name(handler)}")
