"""Ошибки, связанные с операциями над данными."""
from poptimizer.core import exceptions


class DataError(exceptions.POError):
    """Базовая ошибка, связанная с обновлением данных."""


class DataUpdateError(DataError):
    """Ошибка сервисов обновления данных."""


class DataEditError(DataError):
    """Ошибка сервисов редактирования данных."""
