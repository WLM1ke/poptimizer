"""Абстрактный класс признака."""
from abc import ABC, abstractmethod

from torch import Tensor

from poptimizer.dl.params import ModelParams


class Feature(ABC):
    """Абстрактный класс признака."""

    def __init__(self, ticker: str, params: ModelParams):
        pass

    @abstractmethod
    def __getitem__(self, item: int) -> Tensor:
        pass

    @property
    def name(self) -> str:
        """Наименование признака."""
        return self.__class__.__name__
