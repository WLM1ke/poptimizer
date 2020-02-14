"""Абстрактный класс признака."""
from abc import ABC, abstractmethod

from torch import Tensor

from poptimizer.dl.data_params import DataParams


class Feature(ABC):
    """Абстрактный класс признака."""

    # noinspection PyUnusedLocal
    def __init__(self, ticker: str, params: DataParams):
        pass

    @abstractmethod
    def __getitem__(self, item: int) -> Tensor:
        pass

    @property
    def name(self) -> str:
        """Наименование признака."""
        return self.__class__.__name__
