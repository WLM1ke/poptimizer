import asyncio
import logging
from collections import defaultdict
from datetime import timedelta
from typing import (
    Any,
    Final,
    Protocol,
    get_type_hints,
)

from poptimizer.adapters import adapter
from poptimizer.domain import domain

_DEFAULT_FIRST_RETRY: Final = timedelta(seconds=30)
_DEFAULT_BACKOFF_FACTOR: Final = 2


class MsgHandler[M: domain.Msg](Protocol):
    async def __call__(self, msg: M) -> None: ...


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
        self._handlers: dict[adapter.Component, list[tuple[MsgHandler[Any], type[Policy]]]] = defaultdict(list)

    def add_event_handler[E: domain.Msg](
        self,
        handler: MsgHandler[E],
        policy_type: type[Policy],
    ) -> None:
        msg_type = get_type_hints(handler.__call__)["msg"]
        msg_name = adapter.get_component_name(msg_type)

        self._handlers[msg_name].append((handler, policy_type))
        self._lgr.info(
            "%s was registered for %s with %s",
            adapter.get_component_name(handler),
            msg_name,
            adapter.get_component_name(policy_type),
        )

    def publish(self, msg: domain.Msg) -> None:
        self._tg.create_task(self._route(msg))

    async def _route(self, msg: domain.Msg) -> None:
        name = adapter.get_component_name(msg)
        self._lgr.info("%r published", msg)

        for handler, policy_type in self._handlers[name]:
            self._tg.create_task(self._handle(handler, msg, policy_type()))

    async def _handle(
        self,
        handler: MsgHandler[Any],
        msg: domain.Msg,
        policy: Policy,
    ) -> None:
        attempt = 0

        while err := await self._handled_safe(handler, msg):
            attempt += 1
            self._lgr.warning(
                "%s can't handle %r in %d attempt with %s",
                adapter.get_component_name(handler),
                msg,
                attempt,
                err,
            )

            if not await policy.try_again():
                break

        self._lgr.info(
            "%s handled %r",
            adapter.get_component_name(handler),
            msg,
        )

    async def _handled_safe(
        self,
        handler: MsgHandler[Any],
        msg: domain.Msg,
    ) -> str | None:
        error_msg: str | None = None
        try:
            await handler(msg)
        except* domain.POError as err:
            error_msg = f"{", ".join(map(str, err.exceptions))}"

        return error_msg
