"""Контекстный менеджер для подавления системных сигналов SIGINT и SIGTERM для asyncio.loop."""
import asyncio
import logging
import signal
from contextlib import asynccontextmanager
from typing import AsyncIterator, Final

_SIGNALS: Final = (signal.SIGINT, signal.SIGTERM)


@asynccontextmanager
async def suppressor(logger: logging.Logger) -> AsyncIterator[asyncio.Event]:
    """Подавляет действие системных сигналов SIGINT и SIGTERM для asyncio.loop.

    При поступлении системных сигналов устанавливает событие, чтобы асинхронные функции могли отреагировать на это
    корректным завершением.
    """
    loop = asyncio.get_event_loop()

    stop_event = asyncio.Event()

    for add_sig in _SIGNALS:
        loop.add_signal_handler(add_sig, _signal_handler, logger, stop_event)

    try:
        yield stop_event
    finally:

        for remove_sig in _SIGNALS:
            loop.remove_signal_handler(remove_sig)

        logger.info("shutdown completed")


def _signal_handler(logger: logging.Logger, stop_event: asyncio.Event) -> None:
    logger.info("shutdown signal received...")
    stop_event.set()
