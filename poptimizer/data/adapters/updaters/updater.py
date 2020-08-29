"""Базовый класс загрузки данных."""
import logging

import pandas as pd

from poptimizer.data.ports import base, infrustructure


class BaseUpdater(infrustructure.AbstractUpdater):
    """Базовый класс для обновления данных."""

    def __init__(self) -> None:
        """Создается логгер с именем класса."""
        self._logger = logging.getLogger(self.__class__.__name__)

    def __call__(self, table_name: base.TableName) -> pd.DataFrame:
        """Получение необходимых данных для обновления."""
        raise NotImplementedError

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
