"""Ошибки, связанные с операциями над данными."""
from poptimizer.core import exceptions


class DataError(exceptions.POError):
    """Базовая ошибка, связанная с обновлением данных."""


class UpdateError(DataError):
    """Ошибка сервисов обновления данных."""


class EditError(DataError):
    """Ошибка сервисов редактирования данных."""
