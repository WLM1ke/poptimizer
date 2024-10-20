import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import (
    Any,
    Final,
    Protocol,
    get_type_hints,
)

from poptimizer.core import domain, errors

_DEFAULT_FIRST_RETRY: Final = timedelta(seconds=30)
_DEFAULT_BACKOFF_FACTOR: Final = 2


type EventHandler[E: domain.Event] = Callable[[E], Awaitable[None]]


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
    def __init__(self, tg: asyncio.TaskGroup) -> None:
        self._lgr = logging.getLogger()
        self._tg = tg
        self._event_handlers: dict[domain.Component, list[tuple[EventHandler[Any], type[Policy]]]] = defaultdict(list)

    def add_event_handler[E: domain.Event](
        self,
        handler: EventHandler[E],
        policy_type: type[Policy],
    ) -> None:
        event_type = get_type_hints(handler)["event"]
        event_name = domain.get_component_name(event_type)

        self._event_handlers[event_name].append((handler, policy_type))
        self._lgr.info(
            "%s was registered for %s with %s",
            domain.get_component_name(handler),
            event_name,
            domain.get_component_name(policy_type),
        )

    def publish(self, event: domain.Event) -> None:
        self._tg.create_task(self._route_event(event))

    async def _route_event(self, event: domain.Event) -> None:
        event_name = domain.get_component_name(event)
        self._lgr.info("%r published", event)

        for handler, policy_type in self._event_handlers[event_name]:
            self._tg.create_task(self._handle_event(handler, event, policy_type()))

    async def _handle_event(
        self,
        handler: EventHandler[Any],
        event: domain.Event,
        policy: Policy,
    ) -> None:
        attempt = 0

        while err := await self._handled_safe(handler, event):
            attempt += 1
            self._lgr.warning(
                "%s can't handle %r in %d attempt with %s",
                domain.get_component_name(handler),
                event,
                attempt,
                err,
            )

            if not await policy.try_again():
                break

        self._lgr.info(
            "%s handled %r",
            domain.get_component_name(handler),
            event,
        )

    async def _handled_safe(
        self,
        handler: EventHandler[Any],
        event: domain.Event,
    ) -> str | None:
        error_msg: str | None = None
        try:
            await handler(event)
        except* errors.POError as err:
            error_msg = f"{", ".join(map(str, err.exceptions))}"

        return error_msg
