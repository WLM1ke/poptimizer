import asyncio
import zoneinfo
from datetime import datetime, timedelta
from typing import Final, Protocol

from poptimizer.runtime.runner import Step

_MOEX_TZ: Final = zoneinfo.ZoneInfo(key="Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 01.00
_PUBLICATION_HOUR: Final = 1


class Runner[R](Protocol):
    async def __call__[**P, T](self, step: Step[R, P, T], *args: P.args, **kwargs: P.kwargs) -> T: ...


class DayStart[R](Protocol):
    async def __call__(self, runner: Runner[R]) -> None: ...


class Loop[R](Protocol):
    async def __call__(self, runner: Runner[R], stop: asyncio.Event) -> None: ...


class Supervisor[R]:
    def __init__(
        self,
        runner: Runner[R],
        migrations: Step[R, [], None],
        probe: Step[R, [], bool],
        day_start: DayStart[R],
        *loops: Loop[R],
    ) -> None:
        self._runner = runner
        self._migrations = migrations
        self._probe = probe
        self._day_start = day_start
        self._loops = loops

    async def __call__(self, stop: asyncio.Event) -> None:
        if stop.is_set():
            return

        await self._runner(self._migrations)

        if await self._runner(self._probe):
            await self._day_start(self._runner)

        while not stop.is_set():
            loop_stop = asyncio.Event()

            async with asyncio.TaskGroup() as tg:
                for loop in self._loops:
                    tg.create_task(loop(self._runner, loop_stop))

                try:
                    if not await self._wait_for_a_new_day(stop):
                        return
                finally:
                    loop_stop.set()

            await self._day_start(self._runner)

    async def _wait_for_a_new_day(self, stop: asyncio.Event) -> bool:
        while True:
            if not await _sleep_until_publication(stop):
                return False

            if await self._runner(self._probe):
                return True


async def _sleep_until_publication(stop: asyncio.Event) -> bool:
    delay = _until_publication(datetime.now(_MOEX_TZ)).total_seconds()

    try:
        async with asyncio.timeout(delay):
            await stop.wait()
    except TimeoutError:
        return True

    return False


def _until_publication(now: datetime) -> timedelta:
    publication = now.replace(hour=_PUBLICATION_HOUR, minute=0, second=0, microsecond=0)
    if publication <= now:
        publication += timedelta(days=1)

    return publication - now
