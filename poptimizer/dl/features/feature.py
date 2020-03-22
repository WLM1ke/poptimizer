"""Абстрактный класс признака."""
import abc

from torch import Tensor

from poptimizer.dl.data_params import DataParams


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

    @staticmethod
    @abc.abstractmethod
    def key() -> str:
        """Ключ по которому нужно сохранять признак."""

    @staticmethod
    @abc.abstractmethod
    def unique() -> bool:
        """Является ли признак единственным для данного ключа."""
