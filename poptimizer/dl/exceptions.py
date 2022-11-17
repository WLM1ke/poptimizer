"""Ошибки, связанные с обучением сетей и подготовкой данных."""
from poptimizer.core import exceptions


class DLError(exceptions.POError):
    """Базовая ошибка, связанные с обучением сетей и подготовкой данных."""


class TooShortHistoryError(DLError):
    """Слишком мало исторических данных для обучения и тестирования модели."""


class WrongFeatLenError(DLError):
    """Длинна признаков отличается от длинны ряда с доходностями."""


class TestLengthMissmatchError(DLError):
    """Длинна тестовых выборок различается у отдельных тикеров."""
