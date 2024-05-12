from typing import Protocol

from poptimizer.domain.entity import entity


class Ctx(Protocol):
    async def get[E: entity.Entity](
        self,
        t_entity: type[E],
        uid: entity.UID | None = None,
    ) -> E: ...
    async def get_for_update[E: entity.Entity](
        self,
        t_entity: type[E],
        uid: entity.UID | None = None,
    ) -> E: ...
    def info(self, msg: str) -> None: ...
    def warn(self, msg: str) -> None: ...
