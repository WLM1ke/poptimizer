import asyncio
import logging
from typing import Protocol

import pytest

from poptimizer.adapters import mongo
from poptimizer.core import domain, errors
from poptimizer.runtime import runner, uow


class Doc(domain.Entity):
    value: int = 0


UID = domain.UID("doc")
COLLECTION = Doc.__name__


class _CountModels(Protocol):
    async def count_models(self) -> int: ...


def _retrier(test_db: mongo.MongoDatabase) -> runner.Retrier[uow.Repo]:
    return runner.Retrier(lambda: uow.UOW(mongo.Store(test_db)), first_delay=0)


async def _count(repo: _CountModels) -> int:
    return await repo.count_models()


async def _flaky(repo: uow.Repo, calls: list[uow.Repo]) -> str:
    calls.append(repo)

    if len(calls) < 3:
        raise errors.ControllersError("db is down")

    return "ok"


async def _mutate_and_fail(repo: uow.Repo, values: list[int]) -> int:
    doc = await repo.get_for_update(Doc, UID)
    doc.value = 10
    values.append(doc.value)

    if len(values) == 1:
        raise errors.ControllersError("db is down")

    return doc.value


async def _raise_controllers_error() -> None:
    raise errors.ControllersError("wrong version")


async def _grouped(repo: uow.Repo, calls: list[uow.Repo]) -> str:
    calls.append(repo)

    if len(calls) == 1:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(_raise_controllers_error())

    return "ok"


async def _raise_value_error() -> None:
    raise ValueError("bug")


async def _half_broken(repo: uow.Repo, calls: list[uow.Repo]) -> None:
    calls.append(repo)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(_raise_controllers_error())
        tg.create_task(_raise_value_error())


async def _broken(repo: uow.Repo, calls: list[uow.Repo]) -> str:
    calls.append(repo)
    raise ValueError("bug")


async def _cancelled(repo: uow.Repo, calls: list[uow.Repo]) -> None:
    calls.append(repo)
    raise asyncio.CancelledError


async def test_a_narrow_repo_protocol_step_fits_the_retrier(test_db: mongo.MongoDatabase) -> None:
    assert await _retrier(test_db)(_count) == 0


async def test_po_error_is_retried_until_success(test_db: mongo.MongoDatabase) -> None:
    calls: list[uow.Repo] = []

    assert await _retrier(test_db)(_flaky, calls) == "ok"
    assert len(calls) == 3


async def test_every_attempt_gets_a_fresh_unit_of_work(test_db: mongo.MongoDatabase) -> None:
    await test_db[COLLECTION].insert_one({"_id": UID, "ver": 0, "value": 1})
    values: list[int] = []

    assert await _retrier(test_db)(_mutate_and_fail, values) == 10

    assert len(values) == 2
    assert await test_db[COLLECTION].find_one({"_id": UID}) == {"_id": UID, "ver": 1, "value": 10}


async def test_exception_group_po_error_is_retried(test_db: mongo.MongoDatabase) -> None:
    calls: list[uow.Repo] = []

    assert await _retrier(test_db)(_grouped, calls) == "ok"
    assert len(calls) == 2


async def test_a_mixed_group_is_not_retried(test_db: mongo.MongoDatabase, caplog: pytest.LogCaptureFixture) -> None:
    calls: list[uow.Repo] = []

    async with asyncio.timeout(1):
        with caplog.at_level(logging.WARNING), pytest.raises(ExceptionGroup) as caught:
            await _retrier(test_db)(_half_broken, calls)

    assert len(calls) == 1
    assert [type(exc) for exc in caught.value.exceptions] == [ValueError]
    assert not caplog.records


async def test_non_poptimizer_error_propagates_at_once(test_db: mongo.MongoDatabase) -> None:
    calls: list[uow.Repo] = []

    async with asyncio.timeout(1):
        with pytest.raises(ValueError, match="bug"):
            await _retrier(test_db)(_broken, calls)

    assert len(calls) == 1


async def test_cancellation_is_not_retried(test_db: mongo.MongoDatabase) -> None:
    calls: list[uow.Repo] = []

    with pytest.raises(asyncio.CancelledError):
        await _retrier(test_db)(_cancelled, calls)

    assert len(calls) == 1


async def test_each_failure_warns_once_with_the_step_name_and_the_next_delay(
    test_db: mongo.MongoDatabase,
    caplog: pytest.LogCaptureFixture,
) -> None:
    calls: list[uow.Repo] = []

    retrier = runner.Retrier(
        lambda: uow.UOW(mongo.Store(test_db)),
        first_delay=0.001,
        factor=4,
        jitter=lambda: 0.5,
    )

    with caplog.at_level(logging.WARNING):
        await retrier(_flaky, calls)

    warnings = [record.getMessage() for record in caplog.records if record.levelno == logging.WARNING]

    assert len(warnings) == 2
    assert "_flaky" in warnings[0]
    assert "0x" not in warnings[0]
    assert "db is down" in warnings[0]
    assert "in 0.001 sec" in warnings[0]
    assert "in 0.002 sec" in warnings[1]
