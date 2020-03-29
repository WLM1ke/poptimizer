"""Абстрактный класс гена."""
import abc
import copy
from dataclasses import dataclass
from typing import Dict, Any, Union, List, Callable, Optional

import numpy as np

ParamsType = Dict[str, Union[Any, "ParamsType"]]


@dataclass(frozen=True)
class GeneParams:
    """Описание гена."""

    path: List[str]
    default_value: float
    phenotype_function: Callable[[float], Any]
    lower_bound: Optional[float]
    upper_bound: Optional[float]


class Chromosome(abc.ABC):
    """Абстрактный класс хромосомы."""

    _GENES: List[GeneParams]

    def __init__(self, gens_params: ParamsType):
        self._params = gens_params.get(self.name(), self.default_params())

    def __str__(self):
        return str(self._params)

    @classmethod
    def name(cls):
        """Название класса гена."""
        return cls.__name__

    @classmethod
    def default_params(cls) -> ParamsType:
        """Параметры по умолчанию для гена.

        Используется в случае расширения генотипа - организмы со более узким генотипом получат
        значения генов по умолчанию. Гены должны генерироваться с небольшой случайной компонентой и
        воспроизводить предыдущий фенотип по умолчанию.
        """
        return {
            gene.path[-1]: make_default_value(gene.default_value) for gene in cls._GENES
        }

    @property
    def params(self):
        """Параметры гена."""
        return self._params

    def set_phenotype(self, phenotype: ParamsType) -> None:
        """Устанавливает параметры модели с соответствующие значению гена значения данного гена."""
        params = self._params
        for gene in self._GENES:
            node = phenotype
            for key in gene.path[:-1]:
                node = phenotype.setdefault(key, {})
            key = gene.path[-1]
            node[key] = gene.phenotype_function(params[key])

    def mutate(
        self,
        base: "Chromosome",
        diff1: "Chromosome",
        diff2: "Chromosome",
        factor: float,
        probability: float,
    ) -> ParamsType:
        """Мутация в соответствии с алгоритмом дифференциальной эволюции"""
        child = copy.deepcopy(self._params)
        base, diff1, diff2 = base.params, diff1.params, diff2.params
        gens = self._GENES

        flags = np.random.rand(len(gens))
        flags = map(lambda x: x < probability, flags)
        for flag, gene in zip(flags, gens):
            if flag:
                key = gene.path[-1]
                value = base[key] + (diff1[key] - diff2[key]) * factor
                if gene.lower_bound is not None and value < gene.lower_bound:
                    value = (base[key] + gene.lower_bound) / 2
                if gene.upper_bound is not None and value > gene.upper_bound:
                    value = (base[key] + gene.upper_bound) / 2
                child[key] = value
        return child


def make_default_value(mean, relative_range: int = 0.1):
    """Случайное значение в окрестности заданного."""
    return np.random.uniform(mean * (1 - relative_range), mean * (1 + relative_range))
