"""Основная точка входа для запуска приложения."""
from __future__ import annotations

import asyncio
import logging
import signal
import types
from typing import Final

from poptimizer.data import updater

_URI: Final = "mongodb://localhost:27017"


class App:
    """Асинхронное приложение-контекстные менеджер, которое может быть остановлено SIGINT и SIGTERM."""

    def __init__(self) -> None:
        """Инициализирует приложение."""
        logging.basicConfig(level=logging.INFO)
        self._logger = logging.getLogger("App")
        self._stop_event = asyncio.Event()

    async def __aenter__(self) -> App:
        """Организует перехват системных сигналов для корректного завершения работы."""
        loop = asyncio.get_event_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._signal_handler)

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
        await updater.Updater().run(self._stop_event)

    def _signal_handler(self) -> None:
        self._logger.info("shutdown signal received")

        self._stop_event.set()


async def main() -> None:
    """Запускает эволюцию с остановкой по SIGINT и SIGTERM."""
    async with App() as app:
        await app.run()


if __name__ == "__main__":
    asyncio.run(main())
