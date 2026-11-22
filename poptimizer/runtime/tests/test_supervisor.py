import asyncio
from datetime import datetime, timedelta
from typing import cast

import pytest

from poptimizer.core import errors
from poptimizer.runtime import supervisor, uow
from poptimizer.runtime.runner import Step
from poptimizer.runtime.supervisor import Runner

_until_publication = supervisor._until_publication  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
_sleep_until_publication = supervisor._sleep_until_publication  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]


class ScriptedProbe:
    def __init__(self, answers: list[bool]) -> None:
        self._answers = answers

    async def __call__(
        self,
        repo: uow.Repo,  # noqa: ARG002
    ) -> bool:
        assert self._answers, "probe script exhausted"

        return self._answers.pop(0)


class ScriptedSleep:
    def __init__(self, sleeps: list[bool]) -> None:
        self._sleeps = sleeps

    async def __call__(self, stop: asyncio.Event) -> bool:
        await asyncio.sleep(0)

        if not self._sleeps:
            stop.set()

            return False

        return self._sleeps.pop(0)


class RecordingDayStart:
    def __init__(self, log: list[str]) -> None:
        self._log = log

    async def __call__(
        self,
        runner: Runner[uow.Repo],  # noqa: ARG002
    ) -> None:
        self._log.append("day start")


class RecordingRunner:
    async def __call__[**P, T](self, step: Step[uow.Repo, P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        return await step(cast("uow.Repo", object()), *args, **kwargs)


class RecordingLoop:
    def __init__(self, log: list[str], *, name: str = "loop", fail: bool = False) -> None:
        self._log = log
        self._name = name
        self._fail = fail

    async def __call__(
        self,
        runner: Runner[uow.Repo],  # noqa: ARG002
        stop: asyncio.Event,
    ) -> None:
        assert not stop.is_set()

        self._log.append(f"{self._name} started")

        if self._fail:
            raise ValueError("bug")

        await stop.wait()

        self._log.append(f"{self._name} stopped")


class RecordingMigrations:
    def __init__(self, log: list[str]) -> None:
        self._log = log

    async def __call__(
        self,
        repo: uow.Repo,  # noqa: ARG002
    ) -> None:
        self._log.append("migrations")


def _patch_sleep(monkeypatch: pytest.MonkeyPatch, sleeps: list[bool]) -> None:
    monkeypatch.setattr(supervisor, "_sleep_until_publication", ScriptedSleep(sleeps))


def _ten_milliseconds(_now: datetime) -> timedelta:
    return timedelta(milliseconds=10)


async def _never_publication(_stop: asyncio.Event) -> bool:
    await asyncio.Event().wait()

    return True


async def _set_stop_after(stop: asyncio.Event) -> None:
    await asyncio.sleep(0.001)
    stop.set()


def _supervisor(
    probe: ScriptedProbe,
    log: list[str],
    *loops: supervisor.Loop[uow.Repo],
) -> supervisor.Supervisor[uow.Repo]:
    return supervisor.Supervisor(
        RecordingRunner(),
        RecordingMigrations(log),
        probe,
        RecordingDayStart(log),
        *loops,
    )


def test_the_time_until_publication_is_the_publication_hour_of_the_same_day_before_it() -> None:
    assert _until_publication(datetime(2026, 1, 1, 0, 30)) == timedelta(minutes=30)


def test_the_time_until_publication_moves_to_the_next_day_after_the_publication_hour() -> None:
    assert _until_publication(datetime(2026, 1, 1, 2)) == timedelta(hours=23)


def test_the_time_until_publication_moves_to_the_next_day_at_the_publication_hour_itself() -> None:
    assert _until_publication(datetime(2026, 1, 1, 1)) == timedelta(days=1)


async def test_a_stop_during_the_wait_is_reported() -> None:
    stop = asyncio.Event()
    stop.set()

    assert await _sleep_until_publication(stop) is False


async def test_the_wait_ends_at_the_publication_without_a_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(supervisor, "_until_publication", _ten_milliseconds)

    assert await _sleep_until_publication(asyncio.Event()) is True


async def test_a_stop_set_during_the_wait_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(supervisor, "_until_publication", _ten_milliseconds)
    stop = asyncio.Event()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(_set_stop_after(stop))

        assert await _sleep_until_publication(stop) is False


async def test_every_loop_runs_and_is_stopped_with_the_group(monkeypatch: pytest.MonkeyPatch) -> None:
    log: list[str] = []
    _patch_sleep(monkeypatch, [False])
    sup = _supervisor(
        ScriptedProbe([False]),
        log,
        RecordingLoop(log, name="a"),
        RecordingLoop(log, name="b"),
    )

    await sup(asyncio.Event())

    assert log[0] == "migrations"
    assert sorted(log[1:]) == ["a started", "a stopped", "b started", "b stopped"]


async def test_each_run_gives_the_loops_a_fresh_stop_event(monkeypatch: pytest.MonkeyPatch) -> None:
    log: list[str] = []
    _patch_sleep(monkeypatch, [True, True, False])
    sup = _supervisor(ScriptedProbe([False, True, True]), log, RecordingLoop(log, name="a"))

    await sup(asyncio.Event())

    assert log == [
        "migrations",
        "a started",
        "a stopped",
        "day start",
        "a started",
        "a stopped",
        "day start",
        "a started",
        "a stopped",
    ]


async def test_a_loop_failure_propagates_and_stops_the_group(monkeypatch: pytest.MonkeyPatch) -> None:
    log: list[str] = []
    _patch_sleep(monkeypatch, [False])
    sup = _supervisor(
        ScriptedProbe([False]),
        log,
        RecordingLoop(log, name="a"),
        RecordingLoop(log, name="b", fail=True),
    )

    with pytest.raises(ExceptionGroup) as err:
        await sup(asyncio.Event())

    assert isinstance(errors.get_root_error(err.value), ValueError)
    assert log == ["migrations", "a started", "b started"]


async def test_migrations_run_before_the_first_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    log: list[str] = []
    _patch_sleep(monkeypatch, [False])

    await _supervisor(ScriptedProbe([False]), log)(asyncio.Event())

    assert log == ["migrations"]


async def test_the_boot_probe_runs_the_day_start_before_the_loops_start(monkeypatch: pytest.MonkeyPatch) -> None:
    log: list[str] = []
    _patch_sleep(monkeypatch, [False])
    sup = _supervisor(ScriptedProbe([True]), log, RecordingLoop(log))

    await sup(asyncio.Event())

    assert log == ["migrations", "day start", "loop started", "loop stopped"]


async def test_silence_then_a_new_day_stops_the_loops_runs_the_day_start_and_restarts_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log: list[str] = []
    _patch_sleep(monkeypatch, [True, True])
    sup = _supervisor(ScriptedProbe([False, False, True]), log, RecordingLoop(log))

    await sup(asyncio.Event())

    assert log == ["migrations", "loop started", "loop stopped", "day start", "loop started", "loop stopped"]


async def test_a_stop_during_the_sleep_returns_without_the_day_start(monkeypatch: pytest.MonkeyPatch) -> None:
    log: list[str] = []
    _patch_sleep(monkeypatch, [False])
    sup = _supervisor(ScriptedProbe([False]), log, RecordingLoop(log))

    await sup(asyncio.Event())

    assert log == ["migrations", "loop started", "loop stopped"]


async def test_a_stop_before_the_start_runs_nothing() -> None:
    log: list[str] = []
    stop = asyncio.Event()
    stop.set()
    sup = _supervisor(ScriptedProbe([]), log, RecordingLoop(log))

    await sup(stop)

    assert log == []


async def test_a_loop_failure_propagates_at_once(monkeypatch: pytest.MonkeyPatch) -> None:
    log: list[str] = []
    monkeypatch.setattr(supervisor, "_sleep_until_publication", _never_publication)
    sup = _supervisor(ScriptedProbe([False]), log, RecordingLoop(log, fail=True))

    async with asyncio.timeout(1):
        with pytest.raises(ExceptionGroup) as err:
            await sup(asyncio.Event())

    assert isinstance(errors.get_root_error(err.value), ValueError)
    assert log == ["migrations", "loop started"]
