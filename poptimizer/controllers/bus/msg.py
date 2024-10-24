import asyncio
import logging
from collections import defaultdict
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
from poptimizer.use_cases.handler import Ctx, Msg
from poptimizer.controllers.bus import uow

_DEFAULT_FIRST_RETRY: Final = timedelta(seconds=30)
_DEFAULT_BACKOFF_FACTOR: Final = 2


class MsgHandler[M: Msg](Protocol):
    async def __call__(self, ctx: Ctx, msg: M) -> None: ...


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
        tg: asyncio.TaskGroup,
        repo: mongo.Repo,
    ) -> None:
        self._lgr = logging.getLogger()
        self._uow_factory = uow.Factory(repo, self)
        self._tg = tg
        self._handlers: dict[adapter.Component, list[tuple[MsgHandler[Any], type[Policy]]]] = defaultdict(list)

    def register_handler[E: Msg](
        self,
        handler: MsgHandler[E],
        policy_type: type[Policy],
    ) -> None:
        if not (msg_type := get_type_hints(handler.__call__).get("msg")):
            msg_type = get_type_hints(handler)["msg"]

        msg_type_union = get_args(msg_type)
        if not msg_type_union:
            msg_type_union = (msg_type,)

        for msg_subtype in msg_type_union:
            msg_name = adapter.get_component_name(msg_subtype)

            self._handlers[msg_name].append((handler, policy_type))
            self._lgr.info(
                "%s was registered for %s with %s",
                adapter.get_component_name(handler),
                msg_name,
                adapter.get_component_name(policy_type),
            )

    def publish(self, msg: Msg) -> None:
        self._tg.create_task(self._route(msg))

    async def _route(self, msg: Msg) -> None:
        name = adapter.get_component_name(msg)
        self._lgr.info("%r published", msg)

        for handler, policy_type in self._handlers[name]:
            self._tg.create_task(self._handle(handler, msg, policy_type()))

    async def _handle(
        self,
        handler: MsgHandler[Any],
        msg: Msg,
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
        msg: Msg,
    ) -> str | None:
        error_msg: str | None = None
        try:
            async with self._uow_factory() as ctx:
                await handler(ctx, msg)
        except* errors.POError as err:
            error_msg = f"{", ".join(map(str, err.exceptions))}"

        return error_msg
