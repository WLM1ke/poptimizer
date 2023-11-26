from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Any,
    Protocol,
    Self,
    TypeVar,
    cast,
    get_type_hints,
)

from poptimizer.core import domain, errors

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

TEntity = TypeVar("TEntity", bound=domain.Entity)
TEvent_contra = TypeVar("TEvent_contra", bound=domain.Event, contravariant=True)
TResponse_co = TypeVar("TResponse_co", bound=domain.Response, covariant=True)
TRequest_contra = TypeVar("TRequest_contra", bound=domain.Request[Any], contravariant=True)


class EventHandler(Protocol[TEvent_contra]):
    async def handle(self, ctx: domain.Ctx, event: TEvent_contra) -> None:
        """Обрабатывает событие."""


class RequestHandler(Protocol[TRequest_contra, TResponse_co]):
    async def handle(self, ctx: domain.Ctx, request: TRequest_contra) -> TResponse_co:
        """Отвечает на запрос."""


class EventPublisher(Protocol):
    async def publish(self, bus: Callable[[domain.Event], None]) -> None:
        """Публикует сообщения."""


class Ctx(Protocol):
    async def get(self, t_entity: type[TEntity], uid: domain.UID, *, for_update: bool = True) -> TEntity:
        """Получает агрегат заданного типа с указанным uid."""

    def publish(self, event: domain.Event) -> None:
        """Публикует событие."""

    async def request(self, request: domain.Request[TResponse_co]) -> TResponse_co:
        """Выполняет запрос."""

    async def __aenter__(self) -> Self:
        """Открывает контекст для доступа к доменным объектам и посылке сообщений."""

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        """Сохраняет доменные объекты и посылает сообщения."""


def _message_name(message: type[TEvent_contra | TRequest_contra]) -> str:
    return message.__qualname__


class Bus:
    def __init__(self, uow_factory: Callable[[domain.Subdomain, Bus], Ctx]) -> None:
        self._tasks = asyncio.TaskGroup()

        self._uow_factory = uow_factory

        self._event_handlers: dict[str, list[tuple[domain.Subdomain, EventHandler[Any]]]] = defaultdict(list)
        self._request_handlers: dict[str, tuple[domain.Subdomain, RequestHandler[Any, Any]]] = {}
        self._publisher_tasks: list[asyncio.Task[None]] = []

    def add_event_handler(
        self,
        subdomain: domain.Subdomain,
        event_handler: EventHandler[TEvent_contra],
    ) -> None:
        event_type = get_type_hints(event_handler.handle)["event"]
        event_name = _message_name(event_type)
        self._event_handlers[event_name].append((subdomain, event_handler))

    def add_request_handler(
        self,
        subdomain: domain.Subdomain,
        request_handler: RequestHandler[TRequest_contra, TResponse_co],
    ) -> None:
        request_type = get_type_hints(request_handler.handle)["request"]
        request_name = _message_name(request_type)
        if request_name in self._request_handlers:
            raise errors.AdaptersError(f"can't register second handler for {request_name}")

        self._request_handlers[request_name] = (subdomain, request_handler)

    def add_event_publisher(
        self,
        publisher: EventPublisher,
    ) -> None:
        publisher_task = self._tasks.create_task(publisher.publish(self.publish))
        self._publisher_tasks.append(publisher_task)

    def publish(self, event: domain.Event) -> None:
        self._tasks.create_task(self._route_event(event))

    async def _route_event(self, event: domain.Event) -> None:
        event_name = _message_name(event.__class__)

        async with asyncio.TaskGroup() as tg:
            for subdomain, handler in self._event_handlers[event_name]:
                tg.create_task(self._handle_event(subdomain, handler, event))

    async def _handle_event(self, subdomain: domain.Subdomain, handler: EventHandler[Any], event: domain.Event) -> None:
        async with self._uow_factory(subdomain, self) as ctx:
            await handler.handle(ctx, event)

    async def request(self, request: domain.Request[TResponse_co]) -> TResponse_co:
        request_name = _message_name(request.__class__)
        subdomain, handler = self._request_handlers[request_name]

        async with self._uow_factory(subdomain, self) as ctx:
            resp = await handler.handle(ctx, request)

        return cast(TResponse_co, resp)

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
            return await self._tasks.__aexit__(exc_type, exc_value, traceback)
        except asyncio.CancelledError:
            for publisher_task in self._publisher_tasks:
                publisher_task.cancel()

            return await self._tasks.__aexit__(exc_type, exc_value, traceback)
