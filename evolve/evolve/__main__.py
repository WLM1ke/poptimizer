"""Основная точка входа для запуска приложения."""
import asyncio
import logging
import signal
import types

from evolve.population import evolve

_logger = logging.getLogger("App")


class _TaskCanceler:
    def __init__(self, task: asyncio.Task[None]) -> None:
        self._task = task

        signal.signal(signal.SIGINT, self)
        signal.signal(signal.SIGTERM, self)

    def __call__(self, signal_code: int, frame: None | types.FrameType) -> None:
        _logger.info("shutdown signal received")

        self._task.cancel()


async def main() -> None:
    """Запускает эволюцию с отменой по SIGINT и SIGTERM."""
    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()
    population = evolve.Population()
    evolution = evolve.Evolution(population)

    task = loop.create_task(evolution.run())
    _TaskCanceler(task)

    await task


if __name__ == "__main__":
    asyncio.run(main())
