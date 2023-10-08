from typing import Protocol, TypeVar

from poptimizer.core import domain

TEntity = TypeVar("TEntity", bound=domain.Entity)
TResponse = TypeVar("TResponse", bound=domain.Response)


class Ctx(Protocol):
    async def get(self, t_entity: type[TEntity], uid: str, *, for_update: bool = True) -> TEntity:
        """Получает агрегат заданного типа с указанным uid."""

    def publish(self, event: domain.Event) -> None:
        """Публикует событие."""

    async def request(self, request: domain.Request[TResponse]) -> TResponse:
        """Выполняет запрос."""
