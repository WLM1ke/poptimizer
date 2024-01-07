from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import timedelta
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    Literal,
    Protocol,
    Self,
    cast,
    get_args,
    get_type_hints,
)

from poptimizer.core import domain, errors

if TYPE_CHECKING:
    import logging
    from collections.abc import Callable
    from types import TracebackType


_DEFAULT_FIRST_RETRY: Final = timedelta(seconds=30)
_DEFAULT_BACKOFF_FACTOR: Final = 2


class EventHandler[E: domain.Event](Protocol):
    async def handle(self, ctx: domain.Ctx, event: E) -> None:
        ...


class RequestHandler[Req: domain.Request[Any], Res: domain.Response](Protocol):
    async def handle(self, ctx: domain.Ctx, request: Req) -> Res:
        ...


class EventPublisher(Protocol):
    async def publish(self, bus: Callable[[domain.Event], None]) -> None:
        ...


class Ctx(Protocol):
    async def get[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
        *,
        for_update: bool = True,
    ) -> E:
        ...

    def publish(self, event: domain.Event) -> None:
        ...

    def warn(self, msg: str) -> None:
        ...

    async def request[Res: domain.Response](self, request: domain.Request[Res]) -> Res:
        ...

    async def __aenter__(self) -> Self:
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        ...


class Policy(Protocol):
    def __init__(self) -> None:
        ...

    async def try_again(self) -> bool:
        ...


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
        logger: logging.Logger,
        uow_factory: Callable[[domain.Subdomain, domain.Component, Bus], Ctx],
    ) -> None:
        self._logger = logger
        self._tasks = asyncio.TaskGroup()

        self._uow_factory = uow_factory

        self._event_handlers: dict[
            domain.Component, list[tuple[domain.Subdomain, EventHandler[Any], type[Policy]]]
        ] = defaultdict(list)
        self._request_handlers: dict[domain.Component, tuple[domain.Subdomain, RequestHandler[Any, Any]]] = {}
        self._publisher_tasks: list[asyncio.Task[None]] = []

    def add_event_handler[E: domain.Event](
        self,
        subdomain: domain.Subdomain,
        event_handler: EventHandler[E],
        policy_type: type[Policy],
    ) -> None:
        event_type = get_type_hints(event_handler.handle)["event"]
        event_type_union = get_args(event_type)
        if not event_type_union:
            event_type_union = (event_type,)

        for event_subtype in event_type_union:
            event_name = domain.get_component_name_for_type(event_subtype)
            self._event_handlers[event_name].append((subdomain, event_handler, policy_type))
            self._logger.info(
                "%s was registered for %s with %s",
                domain.get_component_name(event_handler),
                event_name,
                domain.get_component_name_for_type(policy_type),
            )

    def add_request_handler[Req: domain.Request[Any], Res: domain.Response](
        self,
        subdomain: domain.Subdomain,
        request_handler: RequestHandler[Req, Res],
    ) -> None:
        request_type = get_type_hints(request_handler.handle)["request"]
        request_name = domain.get_component_name_for_type(request_type)
        if request_name in self._request_handlers:
            raise errors.AdaptersError(f"can't register second handler for {request_name}")

        self._request_handlers[request_name] = (subdomain, request_handler)
        self._logger.info(
            "%s was registered for %s",
            domain.get_component_name(request_handler),
            request_name,
        )

    def add_event_publisher(
        self,
        publisher: EventPublisher,
    ) -> None:
        publisher_task = self._tasks.create_task(publisher.publish(self.publish))
        self._publisher_tasks.append(publisher_task)
        self._logger.info(
            "%s was registered",
            domain.get_component_name(publisher),
        )

    def publish(self, event: domain.Event) -> None:
        component = domain.get_component_name(event)
        match event:
            case domain.WarningEvent():
                self._logger.warning("%s(%s) published", component, event)
            case _:
                self._logger.info("%s(%s) published", component, event)

        self._tasks.create_task(self._route_event(event))

    async def _route_event(self, event: domain.Event) -> None:
        event_name = domain.get_component_name(event)

        async with asyncio.TaskGroup() as tg:
            for subdomain, handler, policy_factory in self._event_handlers[event_name]:
                tg.create_task(self._handle_event(subdomain, handler, event, policy_factory()))

    async def _handle_event(
        self,
        subdomain: domain.Subdomain,
        handler: EventHandler[Any],
        event: domain.Event,
        policy: Policy,
    ) -> None:
        attempt = 0
        while err := await self._handled_safe(subdomain, handler, event):
            attempt += 1
            self.publish(
                domain.WarningEvent(
                    component=domain.get_component_name(handler),
                    msg=f"can't handle {event} in {attempt} attempt with {err}",
                ),
            )

            if not await policy.try_again():
                break

    async def _handled_safe(
        self,
        subdomain: domain.Subdomain,
        handler: EventHandler[Any],
        event: domain.Event,
    ) -> str | None:
        error_msg: str | None = None
        try:
            async with self._uow_factory(
                subdomain,
                domain.get_component_name(handler),
                self,
            ) as ctx:
                await handler.handle(ctx, event)
        except* errors.POError as err:
            error_msg = f"{", ".join(map(str, err.exceptions))}"

        return error_msg

    async def request[Res: domain.Response](self, request: domain.Request[Res]) -> Res:
        request_name = domain.get_component_name(request)
        subdomain, handler = self._request_handlers[request_name]

        handler = cast(RequestHandler[domain.Request[Res], Res], handler)

        async with self._uow_factory(
            subdomain,
            domain.get_component_name(handler),
            self,
        ) as ctx:
            return await handler.handle(ctx, request)

    async def __aenter__(self) -> Self:
        await self._tasks.__aenter__()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            return await asyncio.shield(self._tasks.__aexit__(exc_type, exc_value, traceback))
        except asyncio.CancelledError:
            for publisher_task in self._publisher_tasks:
                publisher_task.cancel()

            return await self._tasks.__aexit__(exc_type, exc_value, traceback)
