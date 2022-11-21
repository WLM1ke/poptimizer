"""Ошибки, связанные с обучением сетей и подготовкой данных."""
from poptimizer.core import exceptions


class DLError(exceptions.POError):
    """Базовая ошибка, связанные с обучением сетей и подготовкой данных."""


class FeaturesError(DLError):
    """Ошибки, связанные с созданием признаков и обучающих примеров."""


class ModelError(DLError):
    """Ошибки, связанные с созданием, обучением или оценкой моделей."""
