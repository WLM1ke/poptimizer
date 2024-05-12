from typing import Any, Protocol

import pandas as pd

from poptimizer.domain.entity import entity


def get_component_name(component: Any) -> str:
    if isinstance(component, type):
        return component.__name__

    return component.__class__.__name__


class Repo(Protocol):
    async def get[E: entity.Entity](self, t_entity: type[E], uid: entity.UID | None = None) -> E: ...


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


class Viewer(Protocol):
    async def turnover(
        self,
        last_day: entity.Day,
        tickers: tuple[entity.Ticker, ...],
    ) -> pd.DataFrame: ...
    async def close(
        self,
        last_day: entity.Day,
        tickers: tuple[entity.Ticker, ...],
    ) -> pd.DataFrame: ...


class VCtx(Protocol):
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
    @property
    def viewer(self) -> Viewer: ...
