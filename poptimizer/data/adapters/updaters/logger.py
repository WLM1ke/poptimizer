"""Базовый класс загрузки данных."""
import logging

from poptimizer.data.ports import base, outer


class LoggerMixin:
    """Mixin для проверки наименования таблицы и логирования."""

    def __init__(self) -> None:
        """Создается логгер с именем класса."""
        self._logger = logging.getLogger(self.__class__.__name__)

    def _log_and_validate_group(
        self,
        table_name: base.TableName,
        updater_group: base.GroupName,
    ) -> str:
        group, name = table_name
        if group != updater_group:
            raise base.DataError(f"Некорректное имя таблицы для обновления {table_name}")
        self._logger.info(f"Загрузка данных: {table_name}")
        return name
