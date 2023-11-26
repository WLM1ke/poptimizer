import asyncio
from collections.abc import Iterator
from types import TracebackType
from typing import Self, TypeVar

from poptimizer.adapters import message, repo
from poptimizer.core import domain, errors
from poptimizer.io import mongo

TEntity = TypeVar("TEntity", bound=domain.Entity)
TResponse = TypeVar("TResponse", bound=domain.Response)


class IdentityMap:
    def __init__(self) -> None:
        self._seen: dict[tuple[type, domain.UID], tuple[domain.Entity, bool]] = {}
        self._lock = asyncio.Lock()

    def __iter__(self) -> Iterator[domain.Entity]:
        yield from [model for model, for_update in self._seen.values() if for_update]

    async def __aenter__(self) -> Self:
        await self._lock.acquire()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        self._lock.release()

        return False

    def get(
        self,
        t_entity: type[TEntity],
        uid: domain.UID,
        *,
        for_update: bool,
    ) -> TEntity | None:
        entity, update_flag = self._seen.get((t_entity, uid), (None, False))
        if entity is None:
            return None

        if not isinstance(entity, t_entity):
            raise errors.AdaptersError(f"type mismatch in identity map for {t_entity}({uid})")

        self._seen[entity.__class__, entity.uid] = (entity, update_flag or for_update)

        return entity

    def save(self, entity: TEntity, *, for_update: bool) -> None:
        saved, _ = self._seen.get((entity.__class__, entity.uid), (None, False))
        if saved is not None:
            raise errors.AdaptersError(f"can't save to identity map {entity.__class__}({entity.uid})")

        self._seen[entity.__class__, entity.uid] = (entity, for_update)


class UOW:
    def __init__(
        self,
        repo: repo.Mongo,
        identity_map: IdentityMap,
        message_bus: message.Bus,
    ) -> None:
        self._repo = repo
        self._identity_map = identity_map
        self._message_bus = message_bus
        self._events: list[domain.Event] = []

    async def get(self, t_entity: type[TEntity], uid: domain.UID | None, *, for_update: bool = True) -> TEntity:
        uid = uid or domain.UID(t_entity.__qualname__.lower())

        async with self._identity_map as identity_map:
            if loaded := identity_map.get(t_entity, uid, for_update=for_update):
                return loaded

            entity = await self._repo.get(t_entity, uid)

            identity_map.save(entity, for_update=for_update)

        return entity

    def publish(self, event: domain.Event) -> None:
        self._events.append(event)

    async def request(self, request: domain.Request[TResponse]) -> TResponse:
        return await self._message_bus.request(request)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if exc_value is not None:
            return False

        await self._repo.save(self._identity_map)

        for event in self._events:
            self._message_bus.publish(event)

        return True


class UOWFactory:
    def __init__(self, mongo_client: mongo.MongoClient) -> None:
        self._mongo_client = mongo_client

    def __call__(self, subdomain: domain.Subdomain, message_bus: message.Bus) -> UOW:
        return UOW(
            repo.Mongo(self._mongo_client, subdomain),
            IdentityMap(),
            message_bus,
        )
