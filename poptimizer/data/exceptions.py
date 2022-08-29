"""Ошибки, связанные с операциями над данными."""
from poptimizer import exceptions


class DataError(exceptions.POError):
    """Базовая ошибка, связанная с обновлением данных."""


class UpdateError(exceptions.POError):
    """Ошибка при попытке обновить данные."""


class DownloadError(DataError):
    """Ошибка загрузки данных из внешних источников."""


class LoadError(DataError):
    """Ошибка загрузки данных из репозитория."""


class SaveError(DataError):
    """Ошибка сохранения данных в репозиторий."""
