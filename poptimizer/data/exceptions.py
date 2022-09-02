"""Ошибки, связанные с операциями над данными."""
from poptimizer import exceptions


class DataError(exceptions.POError):
    """Базовая ошибка, связанная с обновлением данных."""


class LoadError(DataError):
    """Ошибка загрузки данных из репозитория."""


class SaveError(DataError):
    """Ошибка сохранения данных в репозиторий."""


class UpdateError(DataError):
    """Ошибка сервисов обновления данных."""
