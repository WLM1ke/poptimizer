"""Асинхронное логирование."""
import asyncio
import logging


class AsyncLogger:
    """Асинхронное логирование в отдельном потоке."""

    def __init__(self, name: str) -> None:
        """Инициализация логгера."""
        self._logger = logging.getLogger(name)

    def log(self, message: str) -> None:
        """Создает асинхронную задачу по логгированию."""
        asyncio.create_task(self._logging_task(message))

    async def _logging_task(self, message: str) -> None:
        """Задание по логгированию."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._logger.info, message)
