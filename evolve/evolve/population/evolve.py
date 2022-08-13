"""Основной процесс эволюции."""
import asyncio
import logging

_logger = logging.getLogger("Evolve")


class Evolution:
    """Эволюция - бесконечный процесс создания и обора новых моделей для прогноза."""

    def __init__(self) -> None:
        """Инициализирует эволюцию."""
        self._run = True

    async def __call__(self) -> None:
        """Запускает бесконечный процесс эволюцию и CancelledError для завершения."""
        while self._run:
            _logger.info("running")

            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                _logger.info("stopping")

                self._run = False
