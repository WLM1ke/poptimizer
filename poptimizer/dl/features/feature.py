"""Абстрактный класс признака."""
import abc
import enum

from torch import Tensor

from poptimizer.dl.data_params import DataParams


class FeatureTypes(enum.Enum):
    """Типы признаков."""

    # noinspection PyMethodParameters
    def _generate_next_value_(name, start, count, last_values):
        return name

    LABEL = enum.auto()
    WEIGHT = enum.auto()
    NUMERICAL = enum.auto()


class Feature(abc.ABC):
    """Абстрактный класс признака."""

    # noinspection PyUnusedLocal
    @abc.abstractmethod
    def __init__(self, ticker: str, params: DataParams):
        pass

    @abc.abstractmethod
    def __getitem__(self, item: int) -> Tensor:
        """Нумерация идет с начала ряда данных в кэше параметров данных."""

    @property
    def name(self) -> str:
        """Наименование признака."""
        return self.__class__.__name__

    @property
    @abc.abstractmethod
    def type(self) -> FeatureTypes:
        """Тип признака.

        Используется моделью для агригации однотипных признаков и подачи на соответствующий вход.
        """
