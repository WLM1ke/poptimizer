"""Асинхронное логирование."""
import asyncio
import logging
from typing import Generic, Type, TypeVar

ObjectType = TypeVar("ObjectType")


class AsyncLogger(Generic[ObjectType]):
    """Асинхронное логирование в отдельном потоке.

    Поддерживает протокол дескриптора для автоматического определения имени класса, в котором он
    является атрибутом.
    """

    def __init__(self) -> None:
        """Инициализация логгера."""
        self._logger = logging.getLogger()

    def __set_name__(self, owner: Type[ObjectType], name: str) -> None:
        """Создает логгер с именем класса, где он является атрибутом."""
        self._logger = logging.getLogger(owner.__name__)

    def __get__(self, instance: ObjectType, owner: Type[ObjectType]) -> "AsyncLogger[ObjectType]":
        """Возвращает себя при обращении к атрибуту."""
        return self

    def log(self, message: str) -> None:
        """Создает асинхронную задачу по логгированию."""
        asyncio.create_task(self._logging_task(message))

    async def _logging_task(self, message: str) -> None:
        """Задание по логгированию."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._logger.info, message)
