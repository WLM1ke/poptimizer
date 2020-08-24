"""Базовый класс загрузки данных."""
import logging

import pandas as pd

from poptimizer.data import ports
from poptimizer.data.ports import TableName


class BaseUpdater(ports.AbstractUpdater):
    """Базовый класс для обновления данных."""

    def __init__(self) -> None:
        """Создается логгер с именем класса."""
        self._logger = logging.getLogger(self.__class__.__name__)

    def __call__(self, table_name: TableName) -> pd.DataFrame:
        """Получение необходимых данных для обновления."""
        raise NotImplementedError
