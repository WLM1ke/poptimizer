"""Асинхронное логирование."""
import asyncio
import logging

from poptimizer.data.ports import outer


class AsyncLogger:
    """Асинхронное логирование в отдельном потоке."""

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def info(self, message: str) -> None:
        """Создает асинхронную задачу по логгированию."""
        asyncio.create_task(self._logging_task(message))

    async def _logging_task(self, message: str) -> None:
        """Задание по логгированию."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._logger.info, message)


class LoaderLoggerMixin:
    """Mixin для проверки наименования таблицы и логирования."""

    def __init__(self) -> None:
        """Создается логгер с именем класса."""
        self._logger = AsyncLogger(self.__class__.__name__)

    def _log_and_validate_group(
        self,
        table_name: outer.TableName,
        loader_group: outer.GroupName,
    ) -> str:
        """Проверка корректности таблицы и логирование начала загрузки."""
        group, name = table_name
        if group != loader_group:
            raise outer.DataError(f"Некорректное имя таблицы для обновления {table_name}")
        self._logger.info(f"Загрузка {table_name}")
        return name
