"""Базовый класс загрузки данных."""
import asyncio
import logging

from poptimizer.data.ports import base


class AsyncLogger:
    """Асинхронное логирование."""

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def info(self, message: str) -> None:
        """Создает асинхронную задачу по логгированию."""
        loop = asyncio.get_running_loop()
        loop.create_task(self._logging_task(message))

    async def _logging_task(self, message: str) -> None:
        """Задание по логгированию."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._logger.info, message)


class LoggerMixin:
    """Mixin для проверки наименования таблицы и логирования."""

    def __init__(self) -> None:
        """Создается логгер с именем класса."""
        self._logger = AsyncLogger(self.__class__.__name__)

    def _log_and_validate_group(
        self,
        table_name: base.TableName,
        loader_group: base.GroupName,
    ) -> str:
        group, name = table_name
        if group != loader_group:
            raise base.DataError(f"Некорректное имя таблицы для обновления {table_name}")
        self._logger.info(f"Загрузка {table_name}")
        return name
