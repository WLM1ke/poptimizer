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
    get_type_hints,
)

from poptimizer.core import domain, errors

if TYPE_CHECKING:
    import logging
    from collections.abc import Callable
    from types import TracebackType

    from poptimizer.io import telegram


_DEFAULT_FIRST_RETRY: Final = timedelta(seconds=30)
_DEFAULT_BACKOFF_FACTOR: Final = 2


class EventHandler[E: domain.Event](Protocol):
    async def handle(self, ctx: domain.Ctx, event: E) -> None:
        ...


class CommandHandler[Cmd: domain.Command[Any], Res: domain.Result](Protocol):
    async def handle(self, ctx: domain.Ctx, cmd: Cmd) -> Res:
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

    async def send[Res: domain.Result](self, cmd: domain.Command[Res]) -> Res:
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


def _message_name[E: domain.Event, Req: domain.Command[Any]](message: type[E | Req]) -> str:
    return message.__qualname__


class Policy(Protocol):
    async def try_again(self) -> bool:
        ...


type PolicyFactory = Callable[[], Policy]


class IgnoreErrorPolicy:
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
        telegram_client: telegram.Client,
        uow_factory: Callable[[domain.Subdomain, Bus], Ctx],
    ) -> None:
        self._logger = logger
        self._telegram_client = telegram_client
        self._tasks = asyncio.TaskGroup()

        self._uow_factory = uow_factory

        self._event_handlers: dict[str, list[tuple[domain.Subdomain, EventHandler[Any], PolicyFactory]]] = defaultdict(
            list
        )
        self._command_handlers: dict[str, tuple[domain.Subdomain, CommandHandler[Any, Any]]] = {}
        self._publisher_tasks: list[asyncio.Task[None]] = []

    def add_event_handler[E: domain.Event](
        self,
        subdomain: domain.Subdomain,
        event_handler: EventHandler[E],
        policy_factory: PolicyFactory,
    ) -> None:
        event_type = get_type_hints(event_handler.handle)["event"]
        event_name = _message_name(event_type)
        self._event_handlers[event_name].append((subdomain, event_handler, policy_factory))
        self._logger.info(
            "%s was registered for %s with %s",
            event_handler.__class__.__name__,
            event_name,
            policy_factory.__name__,
        )

    def add_command_handler[Cmd: domain.Command[Any], Res: domain.Result](
        self,
        subdomain: domain.Subdomain,
        command_handler: CommandHandler[Cmd, Res],
    ) -> None:
        command_type = get_type_hints(command_handler.handle)["cmd"]
        command_name = _message_name(command_type)
        if command_name in self._command_handlers:
            raise errors.AdaptersError(f"can't register second handler for {command_name}")

        self._command_handlers[command_name] = (subdomain, command_handler)
        self._logger.info(
            "%s was registered for %s",
            command_handler.__class__.__name__,
            command_name,
        )

    def add_event_publisher(
        self,
        publisher: EventPublisher,
    ) -> None:
        publisher_task = self._tasks.create_task(publisher.publish(self.publish))
        self._publisher_tasks.append(publisher_task)
        self._logger.info(
            "%s was registered",
            publisher.__class__.__name__,
        )

    def publish(self, event: domain.Event) -> None:
        self._logger.info("%s(%s) published", event.__class__.__name__, event)
        self._tasks.create_task(self._route_event(event))

    async def _route_event(self, event: domain.Event) -> None:
        event_name = _message_name(event.__class__)

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
            handler_name = handler.__class__.__name__
            attempt += 1

            self._logger.warning("%s attempt %d - %s", handler_name, attempt, err)
            await self._telegram_client.send(handler, attempt, err)

            if not await policy.try_again():
                break

    async def _handled_safe(
        self,
        subdomain: domain.Subdomain,
        handler: EventHandler[Any],
        event: domain.Event,
    ) -> Exception | None:
        try:
            async with self._uow_factory(subdomain, self) as ctx:
                await handler.handle(ctx, event)
        except errors.POError as err:
            return err

        return None

    async def send[Res: domain.Result](self, cmd: domain.Command[Res]) -> Res:
        command_name = _message_name(cmd.__class__)
        subdomain, handler = self._command_handlers[command_name]

        handler = cast(CommandHandler[domain.Command[Res], Res], handler)

        async with self._uow_factory(subdomain, self) as ctx:
            return await handler.handle(ctx, cmd)

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
