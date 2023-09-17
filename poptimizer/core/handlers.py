from types import TracebackType
from typing import Protocol, Self, TypeVar

from poptimizer.core import domain

TEntity = TypeVar("TEntity", bound=domain.BaseEntity)


class UOW(Protocol):
    async def get(self, t_entity: type[TEntity], uid: str) -> TEntity:
        """Получает агрегат заданного типа с указанным uid."""

    async def __aenter__(self) -> Self:
        """Все полученные агрегаты, будут сохранены при закрытие контекста."""

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        """Сохраняет все агрегаты, которые были получены в рамках контекста, если не было ошибки."""
