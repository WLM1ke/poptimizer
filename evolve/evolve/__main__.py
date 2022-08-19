"""Основная точка входа для запуска приложения."""
import asyncio
import logging
import signal
import types
from typing import Final

from motor.motor_asyncio import AsyncIOMotorClient

from evolve.population import evolve, population

_URI: Final = "mongodb://localhost:27017"
_DB: Final = "new_evolve"
_COLLECTION = "models"


class App:
    """Асинхронное приложение-контекстные менеджер, которое может быть остановлено SIGINT и SIGTERM."""

    def __init__(self) -> None:
        """Инициализирует приложение."""
        logging.basicConfig(level=logging.INFO)
        self._logger = logging.getLogger("App")
        self._event = asyncio.Event()

    async def __aenter__(self) -> "App":
        """Организует перехват системных сигналов для корректного завершения работы."""
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._signal_handler)

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Логирует выход из контекстного менеджера."""
        self._logger.info("shutdown finished")

    async def run(self) -> None:
        """Запускает приложение."""
        client = AsyncIOMotorClient(
            _URI,
            tz_aware=False,
        )

        pop = population.Population(
            client[_DB][_COLLECTION],
        )
        evaluator = evolve.Evaluator()
        evolution = evolve.Evolution(pop, evaluator)

        await evolution.run(self._event)

    def _signal_handler(self, signal_code: int, frame: None | types.FrameType) -> None:
        self._logger.info("shutdown signal received")

        self._event.set()


async def main() -> None:
    """Запускает эволюцию с остановкой по SIGINT и SIGTERM."""
    async with App() as app:
        await app.run()


if __name__ == "__main__":
    asyncio.run(main())
