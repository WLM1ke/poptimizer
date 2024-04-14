import asyncio
from datetime import timedelta
from enum import Enum, auto
from typing import Final, NewType, Protocol

from pydantic import BaseModel, ConfigDict

from poptimizer.adapters import uow
from poptimizer.core import domain, errors

_FIRST_RETRY: Final = timedelta(seconds=1)
_BACKOFF_FACTOR: Final = 2


class _Action[S: domain.State](Protocol):
    async def __call__(self, ctx: domain.Ctx, state: S) -> None: ...


_DagID = NewType("_DagID", int)
_NodeID = NewType("_NodeID", int)


class _NodeUID(BaseModel):
    dag: _DagID
    node: _NodeID
    model_config = ConfigDict(frozen=True)


class _Node[S: domain.State]:
    def __init__(self, action: _Action[S], *, retry: bool, inputs_count: int) -> None:
        self._action = action
        self._retry = (retry or None) and (_FIRST_RETRY / _BACKOFF_FACTOR)
        self._inputs_count = inputs_count
        self._children: list[_NodeUID] = []

    @property
    def action(self) -> _Action[S]:
        return self._action

    def get_next_retry(self) -> None | timedelta:
        if self._retry is None:
            return None

        self._retry *= _BACKOFF_FACTOR

        return self._retry

    @property
    def inputs_count(self) -> int:
        return self._inputs_count

    @property
    def children(self) -> list[_NodeUID]:
        return self._children

    def add_child(self, node: _NodeUID) -> None:
        self._children.append(node)

    def inputs_left(self) -> int:
        self._inputs_count -= 1

        return self._inputs_count


class _DagStatus(Enum):
    IDLE = auto()
    RUNNING = auto()
    STOPPING = auto()


class Dag[S: domain.State]:
    def __init__(self, ctx_factory: uow.CtxFactory, state: S) -> None:
        self._ctx_factory = ctx_factory
        self._status = _DagStatus.IDLE
        self._state = state
        self._nodes: dict[_NodeUID, _Node[S]] = {}
        self._retry_tasks: set[asyncio.Task[None]] = set()
        self._finished_event = asyncio.Event()

    @property
    def id(self) -> _DagID:
        return _DagID(id(self))

    def add_node_ignore_errors(self, action: _Action[S], *depends: _NodeUID) -> _NodeUID:
        node = _Node(action=action, inputs_count=len(depends), retry=False)

        return self._add_node(node, *depends)

    def add_node_with_retry(self, action: _Action[S], *depends: _NodeUID) -> _NodeUID:
        node = _Node(action=action, inputs_count=len(depends), retry=True)

        return self._add_node(node, *depends)

    def _add_node(self, node: _Node[S], *depends: _NodeUID) -> _NodeUID:
        if self._status != _DagStatus.IDLE:
            raise errors.AdaptersError("Can't add node to running dag")

        if any(uid.dag != self.id for uid in depends):
            raise errors.AdaptersError("Can't add node to dag which depends on other dag")

        if set(depends) - set(self._nodes):
            raise errors.AdaptersError("Can't add node to dag which depends on not existing node")

        uid = _NodeUID(dag=self.id, node=_NodeID(len(self._nodes)))
        self._nodes[uid] = node

        for parent_uid in depends:
            self._nodes[parent_uid].add_child(uid)

        return uid

    async def run(self) -> S:
        try:
            await asyncio.shield(self._run())
        except asyncio.CancelledError:
            self._status = _DagStatus.STOPPING

            for task in self._retry_tasks:
                task.cancel()

        await self._finished_event.wait()

        return self._state

    async def _run(self) -> None:
        async with asyncio.TaskGroup() as tg:
            if self._status != _DagStatus.IDLE:
                raise errors.AdaptersError("Can't run running dag")

            self._status = _DagStatus.RUNNING

            for node in self._nodes.values():
                if not node.inputs_count:
                    tg.create_task(self._run_action(tg, node))

        self._status = _DagStatus.STOPPING
        self._finished_event.set()

    async def _run_action(self, tg: asyncio.TaskGroup, node: _Node[S]) -> None:
        ctx = self._ctx_factory()
        try:
            async with ctx:
                next_call = await node.action(ctx, self._state)

            ctx.info(f"{domain.get_component_name(node.action)} finished")
            if next_call and self._status != _DagStatus.STOPPING:
                self._run_children(tg, node)
        except* errors.POError as err:
            error_msg = f"{", ".join(map(str, err.exceptions))}"
            ctx.warn(f"{domain.get_component_name(node.action)} failed - {error_msg}")

            if self._status != _DagStatus.STOPPING and (next_retry := node.get_next_retry()) is not None:
                ctx.info(f"{domain.get_component_name(node.action)} waiting for retry in {next_retry}")

                retry_task = tg.create_task(self._retry_node(tg, node, next_retry))
                self._retry_tasks.add(retry_task)
                retry_task.add_done_callback(lambda _: self._retry_tasks.remove(retry_task))

    async def _retry_node(self, tg: asyncio.TaskGroup, node: _Node[S], retry_duration: timedelta) -> None:
        await asyncio.sleep(retry_duration.total_seconds())
        tg.create_task(self._run_action(tg, node))

    def _run_children(self, tg: asyncio.TaskGroup, node: _Node[S]) -> None:
        for child_uid in node.children:
            child = self._nodes[child_uid]
            if not child.inputs_left():
                tg.create_task(self._run_action(tg, child))
