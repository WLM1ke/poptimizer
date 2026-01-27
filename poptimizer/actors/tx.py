from collections.abc import Callable
from types import TracebackType

from poptimizer.actors import actor, runner, uow
from poptimizer.domain import domain
from poptimizer.domain.evolve import evolve


class Tx:
    def __init__(
        self,
        repo: uow.Repo,
        sender: Callable[[actor.PID, actor.Message], None],
        pid: actor.PID,
    ) -> None:
        self._repo = repo
        self._sender = sender
        self._pid = pid

        self._uow = uow.UOW(repo)
        self._msgs: list[tuple[actor.PID, actor.Message]] = []

    async def __aenter__(self) -> actor.Ctx:
        self._uow.clear()
        self._msgs.clear()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is None:
            await self._uow.save()

            for pid, msg in self._msgs:
                self._sender(pid, msg)

    def send(self, pid: actor.PID, msg: actor.Message) -> None:
        self._msgs.append((pid, msg))

    def send_self(self, msg: actor.Message) -> None:
        self._msgs.append((self._pid, msg))

    async def run_with_retry[**I, O](
        self,
        handler: runner.Handler[actor.SubCtx, I, O],
        *args: I.args,
        **kwargs: I.kwargs,
    ) -> O:
        tx = Tx(self._repo, self._sender, self._pid)

        return await runner.Runner().run_with_retry(handler, tx, *args, **kwargs)

    async def get[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        return await self._uow.get(t_entity, uid)

    async def get_for_update[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        return await self._uow.get_for_update(t_entity, uid)

    async def delete(self, entity: domain.Entity) -> None:
        await self._uow.delete(entity)

    async def count_models(self) -> int:
        return await self._uow.count_models()

    async def next_model_for_update(self, uid: domain.UID) -> tuple[evolve.Model, bool]:
        return await self._uow.next_model_for_update(uid)

    async def sample_models(self, n: int) -> list[evolve.Model]:
        return await self._uow.sample_models(n)
