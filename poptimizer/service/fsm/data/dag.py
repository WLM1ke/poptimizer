import asyncio
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Final, NewType

from pydantic import BaseModel, ConfigDict

from poptimizer.adapter import adapter
from poptimizer.domain import consts
from poptimizer.domain.service import domain_service
from poptimizer.service.common import service, uow

_FIRST_RETRY: Final = timedelta(seconds=1)
_BACKOFF_FACTOR: Final = 2


type _Action[P] = Callable[[domain_service.VCtx, P], Awaitable[None]]

_DagID = NewType("_DagID", int)
_NodeID = NewType("_NodeID", int)


class _NodeUID(BaseModel):
    dag: _DagID
    node: _NodeID
    model_config = ConfigDict(frozen=True)


class _Node[P]:
    def __init__(self, action: _Action[P], *, retry: bool, inputs_count: int) -> None:
        self._action = action
        self._retry = (retry or None) and (_FIRST_RETRY / _BACKOFF_FACTOR)
        self._inputs_count = inputs_count
        self._children: list[_NodeUID] = []

    @property
    def action(self) -> _Action[P]:
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


class Dag[P]:
    def __init__(self, ctx_factory: uow.CtxFactory, params: P) -> None:
        self._ctx_factory = ctx_factory
        self._params = params
        self._nodes: dict[_NodeUID, _Node[P]] = {}
        self._tg = asyncio.TaskGroup()
        self._started = False
        self._stopping = False
        self._retry_tasks: set[asyncio.Task[None]] = set()

    @property
    def id(self) -> _DagID:
        return _DagID(id(self))

    def add_node_ignore_errors(self, action: _Action[P], *depends: _NodeUID) -> _NodeUID:
        node = _Node(action=action, inputs_count=len(depends), retry=False)

        return self._add_node(node, *depends)

    def add_node_with_retry(self, action: _Action[P], *depends: _NodeUID) -> _NodeUID:
        node = _Node(action=action, inputs_count=len(depends), retry=True)

        return self._add_node(node, *depends)

    def _add_node(self, node: _Node[P], *depends: _NodeUID) -> _NodeUID:
        if self._started:
            raise service.ServiceError("can't add node to running dag")

        if any(uid.dag != self.id for uid in depends):
            raise service.ServiceError("can't add node to dag which depends on other dag")

        if set(depends) - set(self._nodes):
            raise service.ServiceError("can't add node to dag which depends on not existing node")

        uid = _NodeUID(dag=self.id, node=_NodeID(len(self._nodes)))
        self._nodes[uid] = node

        for parent_uid in depends:
            self._nodes[parent_uid].add_child(uid)

        return uid

    async def __call__(self) -> P:
        if self._started:
            raise service.ServiceError("can't run running dag")

        self._started = True
        run_task = asyncio.create_task(self._run())
        try:
            await asyncio.shield(run_task)
        except asyncio.CancelledError:
            self._stopping = True

            for task in self._retry_tasks:
                task.cancel()

            await run_task

            raise

        return self._params

    async def _run(self) -> None:
        async with self._tg:
            for node in self._nodes.values():
                if not node.inputs_count:
                    self._tg.create_task(self._run_node(node))

    async def _run_node(self, node: _Node[P]) -> None:
        if self._stopping:
            return

        ctx = self._ctx_factory()
        component_name = adapter.get_component_name(node.action)

        try:
            async with ctx:
                await node.action(ctx, self._params)

            ctx.info(f"{component_name} finished")
            self._run_children(node)
        except* consts.POError as err:
            error_msg = f"{", ".join(map(str, err.exceptions))}"
            ctx.warn(f"{component_name} failed - {error_msg}")

            if (next_retry := node.get_next_retry()) is not None and not self._stopping:
                ctx.info(f"{component_name} waiting for retry in {next_retry}")
                retry_task = self._tg.create_task(self._retry_node(node, next_retry))
                self._retry_tasks.add(retry_task)
                retry_task.add_done_callback(lambda _: self._retry_tasks.remove(retry_task))

    async def _retry_node(self, node: _Node[P], retry_duration: timedelta) -> None:
        await asyncio.sleep(retry_duration.total_seconds())
        self._tg.create_task(self._run_node(node))

    def _run_children(self, node: _Node[P]) -> None:
        for child_uid in node.children:
            child = self._nodes[child_uid]
            if not child.inputs_left():
                self._tg.create_task(self._run_node(child))
